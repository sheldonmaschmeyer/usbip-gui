"""Tests for the client tab."""

# pylint: disable=duplicate-code, too-many-lines

import subprocess
import sys
from pathlib import PurePosixPath
from types import TracebackType
from typing import Callable, Literal, Type

from unittest.mock import MagicMock, mock_open, patch
from PyQt6.QtWidgets import QMessageBox
import usbip_gui.gui.client as client_mod
from usbip_gui.common import tunnel_state

from usbip_gui.gui.client import (
    ClientTab,
    parse_remote_list,
    parse_attached_list,
    get_or_create_client_tunnel,
    get_or_create_cloudflared_client_tunnel,
    list_remote_usb,
    list_attached_usb,
    attach_remote_usb,
    detach_remote_usb,
)


@patch("usbip_gui.gui.client.executables.sys")
def test_resolve_usbip_client_executable_linux(mock_sys: MagicMock):
    """Test linux executable resolution."""
    mock_sys.platform = "linux"
    resolve_exe = client_mod.__dict__["_resolve_usbip_client_executable"]
    assert resolve_exe() == "usbip"


@patch("usbip_gui.gui.client.executables.sys")
@patch("usbip_gui.gui.client.executables.shutil.which")
def test_resolve_usbip_client_executable_which_match(
    mock_which: MagicMock, mock_sys: MagicMock
):
    """Test win32 executable resolution uses PATH match when present."""
    mock_sys.platform = "win32"
    mock_which.side_effect = [r"C:\USBip\usbip.exe", None]
    resolve_exe = client_mod.__dict__["_resolve_usbip_client_executable"]
    assert resolve_exe() == r"C:\USBip\usbip.exe"


@patch("usbip_gui.gui.client.executables.sys")
@patch("usbip_gui.gui.client.executables.shutil.which", return_value=None)
@patch("usbip_gui.gui.client.executables.Path.exists")
def test_resolve_usbip_client_executable_candidates(
    mock_exists: MagicMock,
    _mock_which: MagicMock,
    mock_sys: MagicMock,
):
    """Test win32 executable resolution falls back to candidate paths."""
    mock_sys.platform = "win32"
    resolve_exe = client_mod.__dict__["_resolve_usbip_client_executable"]
    with patch.dict(
        "os.environ",
        {
            "ProgramFiles": r"C:\Program Files",
            "ProgramW6432": r"C:\Program Files",
            "ProgramFiles(x86)": r"C:\Program Files (x86)",
        },
        clear=True,
    ):
        # First candidate exists.
        mock_exists.side_effect = [True]
        exe = resolve_exe()
    assert (
        PurePosixPath(exe.replace("\\", "/"))
        .as_posix()
        .endswith("USBip/usbip.exe")
    )


@patch("usbip_gui.gui.client.executables.sys")
@patch("usbip_gui.gui.client.executables.shutil.which", return_value=None)
@patch("usbip_gui.gui.client.executables.Path.exists", return_value=False)
def test_resolve_usbip_client_executable_skips_duplicate_candidates(
    _mock_exists: MagicMock,
    _mock_which: MagicMock,
    mock_sys: MagicMock,
):
    """Test duplicate candidate paths are deduplicated by the resolver."""
    mock_sys.platform = "win32"
    resolve_exe = client_mod.__dict__["_resolve_usbip_client_executable"]
    with patch.dict(
        "os.environ",
        {
            "ProgramFiles": r"C:\Program Files",
            "ProgramW6432": r"C:\Program Files",
            "ProgramFiles(x86)": r"C:\Program Files (x86)",
        },
        clear=True,
    ):
        try:
            resolve_exe()
            assert False, "Expected FileNotFoundError"
        except FileNotFoundError as e:
            msg = str(e)
            checked = [
                line.strip()[2:]
                for line in msg.splitlines()
                if line.strip().startswith("- ")
            ]
            # ProgramFiles and ProgramW6432 point to the same base path,
            # so duplicate exact entries should be collapsed.
            assert len(checked) == len(set(checked))
            assert any("Program Files" in entry for entry in checked)


@patch("usbip_gui.gui.client.executables.sys")
@patch("usbip_gui.gui.client.executables.shutil.which", return_value=None)
@patch("usbip_gui.gui.client.executables.Path.exists", return_value=False)
def test_resolve_usbip_client_executable_not_found(
    _mock_exists: MagicMock,
    _mock_which: MagicMock,
    mock_sys: MagicMock,
):
    """Test win32 executable resolution raises with checked path details."""
    mock_sys.platform = "win32"
    resolve_exe = client_mod.__dict__["_resolve_usbip_client_executable"]
    with patch.dict("os.environ", {}, clear=True):
        try:
            resolve_exe()
            assert False, "Expected FileNotFoundError"
        except FileNotFoundError as e:
            msg = str(e)
            assert "usbip.exe was not found" in msg
            assert "Program Files" in msg


@patch("usbip_gui.gui.client.tab.list_remote_usb", return_value=[])
@patch("usbip_gui.gui.client.tab.list_attached_usb", return_value=[])
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
    assert rows[0] == ("1-1", "05ac:12a8", "Apple, Inc.", "iPhone")
    assert rows[1] == ("2-2.1", "0000:0000", "Mouse", "Generic")

    # Test no exportable
    empty = parse_remote_list("no exportable devices found on host")
    assert not empty

    # Test unknown product on win32
    with patch("usbip_gui.gui.client.sys.platform", "win32"):
        rows = parse_remote_list(
            "1-1: Original Manufacturer : unknown product (1234:5678)"
        )
        assert len(rows) == 1
        assert rows[0] == (
            "1-1",
            "1234:5678",
            "Original",
            "Original Manufacturer",
        )

        # Test generic first word
        rows2 = parse_remote_list(
            "1-1: USB Original Manufacturer : unknown product (1234:5678)"
        )
        assert rows2[0] == (
            "1-1",
            "1234:5678",
            "",
            "USB Original Manufacturer",
        )


def test_parse_attached_list():
    """Test parsing of already attached USB devices."""
    text = "Port 1:\nManufacturer: Desc : Extra\n1-1 -> usb://192.168.1.100\n"
    rows = parse_attached_list(text)
    assert len(rows) == 1
    assert rows[0] == (
        "192.168.1.100",
        1,
        "1-1",
        "",
        "Manufacturer",
        "Desc:Extra",
    )

    # Test unknown product attached on win32
    with patch("usbip_gui.gui.client.sys.platform", "win32"):
        text_attached_unknown = (
            "Port 1:\nBrother, Inc: unknown product (1234:5678) : \n"
            "1-1 -> usb://192.168.1.100\n"
        )
        rows = parse_attached_list(text_attached_unknown)
        assert len(rows) == 1
        assert rows[0] == (
            "192.168.1.100",
            1,
            "1-1",
            "1234:5678",
            "Brother,",
            "Brother",
        )

        # Test generic first word
        text_attached_generic = (
            "Port 1:\nUSB Brother: unknown product (1234:5678) : \n"
            "1-1 -> usb://192.168.1.100\n"
        )
        rows2 = parse_attached_list(text_attached_generic)
        assert rows2[0] == (
            "192.168.1.100",
            1,
            "1-1",
            "1234:5678",
            "",
            "USB Brother",
        )


def test_get_or_create_client_tunnel_insecure():
    """Test get tunnel when secure is False."""
    h, p = get_or_create_client_tunnel("host", 1234, False, "")
    assert h == "host"
    assert p == 1234


@patch("usbip_gui.gui.client.tunnels.socket.create_connection")
@patch("usbip_gui.gui.client.tunnels.ssl.create_default_context")
@patch("usbip_gui.gui.client.tunnels.subprocess.Popen")
@patch("usbip_gui.gui.client.tunnels.tunnel_state")
@patch("usbip_gui.gui.client.tunnels.os.path.exists", return_value=False)
@patch(
    "usbip_gui.gui.client.tunnels.QMessageBox.question",
    return_value=QMessageBox.StandardButton.Yes,
)
@patch("usbip_gui.gui.client.tunnels.os.makedirs")
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


@patch("usbip_gui.gui.client.tunnels.socket.create_connection")
@patch("usbip_gui.gui.client.tunnels.ssl.create_default_context")
@patch("usbip_gui.gui.client.tunnels.subprocess.Popen")
@patch("usbip_gui.gui.client.tunnels.tunnel_state")
@patch(
    "usbip_gui.gui.client.tunnels.QMessageBox.question",
    return_value=QMessageBox.StandardButton.Yes,
)
@patch("usbip_gui.gui.client.tunnels.os.path.exists", return_value=False)
@patch("usbip_gui.gui.client.tunnels.os.makedirs")
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


@patch("usbip_gui.gui.client.tunnels.socket.create_connection")
@patch("usbip_gui.gui.client.tunnels.ssl.create_default_context")
@patch(
    "usbip_gui.gui.client.tunnels.QMessageBox.question",
    return_value=QMessageBox.StandardButton.No,
)
@patch("usbip_gui.gui.client.tunnels.os.path.exists", return_value=False)
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


@patch("usbip_gui.gui.client.tunnels.socket.create_connection")
@patch("usbip_gui.gui.client.tunnels.ssl.create_default_context")
@patch(
    "usbip_gui.gui.client.tunnels.QMessageBox.question",
    return_value=QMessageBox.StandardButton.Yes,
)
@patch("usbip_gui.gui.client.tunnels.QMessageBox.critical")
@patch("usbip_gui.gui.client.tunnels.os.path.exists", return_value=False)
@patch("usbip_gui.gui.client.tunnels.os.makedirs")
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


@patch("usbip_gui.gui.client.operations._resolve_usbip_client_executable")
@patch("usbip_gui.gui.client.operations.get_or_create_client_tunnel")
@patch("usbip_gui.gui.client.subprocess.run")
def test_list_remote_usb(
    mock_run: MagicMock, mock_tunnel: MagicMock, mock_resolve_usbip: MagicMock
):
    """Test list remote usb."""
    mock_resolve_usbip.return_value = "usbip"
    mock_tunnel.return_value = ("127.0.0.1", 1234)
    mock_run.return_value.stdout = "1-1: Man : Desc (00:00)"

    with patch("usbip_gui.gui.client.sys.platform", "linux"):
        res = list_remote_usb("host", 1234)
        assert len(res) == 1
        mock_run.assert_called_with(
            [
                "pkexec",
                "usbip",
                "--tcp-port",
                "1234",
                "list",
                "--remote=127.0.0.1",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    with patch("usbip_gui.gui.client.sys.platform", "win32"):
        res = list_remote_usb("host", 1234)
        assert len(res) == 1
        mock_run.assert_called_with(
            ["usbip", "--tcp-port", "1234", "list", "--remote=127.0.0.1"],
            capture_output=True,
            text=True,
            check=False,
        )

    mock_tunnel.return_value = ("", 0)
    res = list_remote_usb("host", 1234)
    assert len(res) == 0


@patch("usbip_gui.gui.client.subprocess.run")
@patch("usbip_gui.gui.client.operations._resolve_usbip_client_executable")
def test_list_attached_usb(mock_resolve_usbip: MagicMock, mock_run: MagicMock):
    """Test list attached usb."""
    mock_resolve_usbip.return_value = "usbip"
    mock_run.return_value.stdout = ""

    with patch("usbip_gui.gui.client.sys.platform", "linux"):
        list_attached_usb()
        mock_run.assert_called_with(
            ["pkexec", "usbip", "port"],
            capture_output=True,
            text=True,
            check=False,
        )

    with patch("usbip_gui.gui.client.sys.platform", "win32"):
        list_attached_usb()
        mock_run.assert_called_with(
            ["usbip", "port"],
            capture_output=True,
            text=True,
            check=False,
        )


@patch("usbip_gui.gui.client.operations.get_or_create_client_tunnel")
@patch("usbip_gui.gui.client.operations._resolve_usbip_client_executable")
@patch("usbip_gui.gui.client.operations.run_elevated")
def test_attach_remote_usb(
    mock_run_elevated: MagicMock,
    mock_resolve_usbip: MagicMock,
    mock_tunnel: MagicMock,
):
    """Test attach remote usb."""
    mock_resolve_usbip.return_value = "usbip"
    mock_run_elevated.return_value.returncode = 0
    mock_tunnel.return_value = ("127.0.0.1", 1234)
    attach_remote_usb("host", "1-1")
    mock_run_elevated.assert_called_once_with(
        [
            "usbip",
            "--tcp-port",
            "1234",
            "attach",
            "--remote=127.0.0.1",
            "--busid=1-1",
        ]
    )

    mock_run_elevated.reset_mock()
    mock_tunnel.return_value = ("", 0)
    attach_remote_usb("host", "1-1")
    mock_run_elevated.assert_not_called()


@patch("usbip_gui.gui.client.operations._resolve_usbip_client_executable")
@patch("usbip_gui.gui.client.operations.run_elevated")
def test_detach_remote_usb(
    mock_run_elevated: MagicMock, mock_resolve_usbip: MagicMock
):
    """Test detach remote usb."""
    mock_resolve_usbip.return_value = "usbip"
    detach_remote_usb(1)
    mock_run_elevated.assert_called_with(["usbip", "detach", "--port=1"])


@patch("usbip_gui.gui.client.tab.QMessageBox.warning")
def test_check_secure_warning(mock_warning: MagicMock):
    """Test check secure warning."""
    ClientTab.check_secure_warning(MagicMock(), 0)
    mock_warning.assert_called_once()


@patch("usbip_gui.gui.client.tab.SortableTreeWidgetItem")
@patch("usbip_gui.gui.client.tab.list_remote_usb")
@patch("usbip_gui.gui.client.tab.list_attached_usb")
def test_refresh_remote(
    mock_attached_list: MagicMock,
    mock_remote_list: MagicMock,
    mock_item: MagicMock,
):
    """Test refresh remote."""
    mock_remote_list.return_value = [("1-1", "1234:5678", "Man", "Desc")]
    mock_attached_list.return_value = []
    tab = MagicMock()
    tab.remote_ip_input.text.return_value = "localhost"
    tab.remote_port_input.text.return_value = "1234"
    ClientTab.refresh_remote(tab)
    tab.remote_listbox.clear.assert_called_once()
    expected = ["localhost", "1234", "1-1", "Detached", "Man"]
    if sys.platform == "win32":
        expected.append("")
    expected.extend(["Desc", "1234:5678"])
    mock_item.assert_called_once_with(tab.remote_listbox, expected)

    with patch("usbip_gui.gui.client.sys.platform", "win32"):
        with patch(
            "usbip_gui.gui.client.tab.enrich_remote_device_item"
        ) as mock_enrich:
            ClientTab.refresh_remote(tab)
            mock_enrich.assert_called_once()


@patch("usbip_gui.gui.client.tunnels.QMessageBox.critical")
@patch("usbip_gui.gui.client.tab.list_remote_usb")
@patch("usbip_gui.gui.client.tab.list_attached_usb")
def test_refresh_remote_usbip_not_found(
    mock_attached_list: MagicMock,
    mock_remote_list: MagicMock,
    mock_critical: MagicMock,
):
    """Test refresh remote shows a clear error if usbip isn't installed."""
    mock_remote_list.side_effect = FileNotFoundError(
        "[WinError 2] The system cannot find the file specified"
    )
    tab = MagicMock()
    tab.remote_ip_input.text.return_value = "localhost"
    tab.remote_port_input.text.return_value = "1234"
    ClientTab.refresh_remote(tab)
    mock_critical.assert_called_once()
    tab.remote_listbox.clear.assert_not_called()
    mock_attached_list.assert_not_called()


@patch("usbip_gui.gui.client.tunnels.time.sleep")
@patch("usbip_gui.gui.client.tab.attach_remote_usb")
def test_attach_remote_ui(mock_attach: MagicMock, _mock_sleep: MagicMock):
    """Test attach remote from UI."""
    tab = MagicMock()
    tab.remote_port_input.get.return_value = "1234"
    tab.remote_listbox.selection.return_value = ["item1"]
    tab.remote_listbox.item.return_value = {"values": ["1-1"]}
    ClientTab.attach_remote(tab)
    mock_attach.assert_called_once()
    tab.refresh_remote.assert_called_once()


@patch("usbip_gui.gui.client.tunnels.time.sleep")
@patch("usbip_gui.gui.client.tab.detach_remote_usb")
def test_detach_remote_ui(mock_detach: MagicMock, _mock_sleep: MagicMock):
    """Test detach remote from UI."""
    tab = MagicMock()
    tab.remote_listbox.selectedItems.return_value = [MagicMock()]
    tab.remote_listbox.selectedItems.return_value[0].text.return_value = (
        "Attached"
    )
    tab.remote_listbox.selectedItems.return_value[0].data.return_value = 1
    ClientTab.detach_remote(tab)
    mock_detach.assert_called_once_with(1)
    tab.refresh_remote.assert_called_once()


def test_on_double_click_remote():
    """Test remote double click."""
    tab = MagicMock()
    tab.remote_listbox.selection.return_value = ["item"]
    ClientTab.on_double_click_remote(tab, MagicMock(), 0)
    tab.attach_remote.assert_called_once()


def test_parse_remote_list_short():
    """Test parse short remote list."""
    res = parse_remote_list("1-1: a: b")  # length 3
    assert not res


@patch("usbip_gui.gui.client.tunnels.socket.create_connection")
@patch("usbip_gui.gui.client.tunnels.ssl.create_default_context")
@patch("usbip_gui.gui.client.tunnels.QMessageBox.critical")
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


@patch("usbip_gui.gui.client.tunnels.time.sleep")
@patch("usbip_gui.gui.client.tunnels.threading.Thread")
@patch("usbip_gui.gui.client.tunnels.subprocess.Popen")
@patch("usbip_gui.gui.client.tunnels.tunnel_state")
@patch("usbip_gui.gui.client.tunnels.socket.create_connection")
@patch("usbip_gui.gui.client.tunnels.ssl.create_default_context")
@patch(
    "usbip_gui.gui.client.tunnels.QMessageBox.question",
    return_value=QMessageBox.StandardButton.Yes,
)
@patch("usbip_gui.gui.client.tunnels.os.path.exists", return_value=False)
@patch("usbip_gui.gui.client.tunnels.os.makedirs")
@patch("builtins.open", new_callable=mock_open, read_data="{}")
def test_get_or_create_client_tunnel_secure_win32_fallback_port(
    _mock_open: MagicMock,
    _mock_makedirs: MagicMock,
    _mock_exists: MagicMock,
    _mock_ask: MagicMock,
    mock_ctx: MagicMock,
    mock_conn: MagicMock,
    mock_tunnel: MagicMock,
    _mock_popen: MagicMock,
    mock_thread: MagicMock,
    _mock_sleep: MagicMock,
):
    """Test secure tunnel retries 3241 on WinError 10054 from port 3240."""
    mock_tunnel.client_processes = {}

    first_error = ConnectionResetError("forcibly closed")
    first_error.winerror = 10054  # type: ignore[attr-defined]
    mock_conn.side_effect = [first_error, MagicMock(), MagicMock()]

    mock_ssock = (
        mock_ctx.return_value.wrap_socket.return_value.__enter__.return_value
    )
    mock_ssock.getpeercert.return_value = b"mock_cert_der"
    mock_ssock.recv.return_value = b"\x01"

    with patch("usbip_gui.gui.client.sys.platform", "win32"):
        host, local_port = get_or_create_client_tunnel(
            "host", 3240, True, "pass"
        )

    assert host == "127.0.0.1"
    assert local_port > 0
    assert mock_conn.call_args_list[0].args[0] == ("host", 3240)
    assert mock_conn.call_args_list[1].args[0] == ("host", 3241)
    mock_thread.assert_called_once()


@patch("usbip_gui.gui.client.tunnels.socket.create_connection")
@patch("usbip_gui.gui.client.tunnels.ssl.create_default_context")
@patch("usbip_gui.gui.client.tunnels.QMessageBox.critical")
def test_get_or_create_client_tunnel_secure_win32_all_fail(
    mock_critical: MagicMock,
    _mock_ctx: MagicMock,
    mock_conn: MagicMock,
):
    """Test win32 secure tunnel failure shows TLS setup tip for 3240/3241."""
    err = ConnectionResetError("forcibly closed")
    err.winerror = 10054  # type: ignore[attr-defined]
    mock_conn.side_effect = [err, err]
    with patch("usbip_gui.gui.client.sys.platform", "win32"):
        host, port = get_or_create_client_tunnel("host", 3240, True, "pw")
    assert host == ""
    assert port == 0
    assert mock_critical.called
    details = mock_critical.call_args.args[2]
    assert "Windows secure mode may listen on port 3241" in details


@patch("usbip_gui.gui.client.tunnels.socket.create_connection")
@patch("usbip_gui.gui.client.tunnels.ssl.create_default_context")
@patch(
    "usbip_gui.gui.client.tunnels.QMessageBox.question",
    return_value=QMessageBox.StandardButton.Yes,
)
@patch("usbip_gui.gui.client.tunnels.QMessageBox.critical")
def test_get_or_create_client_tunnel_secure_fingerprint_mismatch(
    mock_critical: MagicMock,
    _mock_question: MagicMock,
    mock_ctx: MagicMock,
    mock_conn: MagicMock,
):
    """Test secure auth check rejects mismatched fingerprint."""
    fake_sock = MagicMock()
    fake_wrapped_first = MagicMock()
    fake_wrapped_second = MagicMock()

    class _SockContext:
        def __enter__(self):
            return fake_sock

        def __exit__(
            self,
            exc_type: Type[BaseException] | None,
            exc: BaseException | None,
            tb: TracebackType | None,
        ) -> Literal[False]:
            return False

    class _WrapContext:
        def __init__(self, wrapped: MagicMock):
            self._wrapped = wrapped

        def __enter__(self):
            return self._wrapped

        def __exit__(
            self,
            exc_type: Type[BaseException] | None,
            exc: BaseException | None,
            tb: TracebackType | None,
        ) -> Literal[False]:
            return False

    fake_wrapped_first.getpeercert.return_value = b"cert-bytes-1"
    fake_wrapped_second.getpeercert.return_value = b"cert-bytes-2"
    ctx = mock_ctx.return_value
    ctx.wrap_socket.side_effect = [
        _WrapContext(fake_wrapped_first),
        _WrapContext(fake_wrapped_second),
    ]
    mock_conn.side_effect = [_SockContext(), _SockContext()]

    with (
        patch(
            "usbip_gui.gui.client.tunnels.os.path.exists",
            return_value=False,
        ),
        patch("builtins.open", mock_open()),
        patch(
            "usbip_gui.gui.client.tunnels._secure_port_candidates",
            return_value=[3240],
        ),
    ):
        host, port = get_or_create_client_tunnel("host", 3240, True, "pw")

    assert host == ""
    assert port == 0
    assert mock_critical.called
    assert "Fingerprint mismatch during auth check" in (
        mock_critical.call_args.args[2]
    )


@patch(
    "usbip_gui.gui.client.tunnels.os.path.exists",
    return_value=QMessageBox.StandardButton.Yes,
)
@patch(
    "builtins.open",
    new_callable=mock_open,
    read_data='{"localhost:1234": "FP"}',
)
@patch("usbip_gui.gui.client.tunnels.socket.create_connection")
@patch("usbip_gui.gui.client.tunnels.ssl.create_default_context")
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
    with patch("usbip_gui.gui.client.tunnels.hashlib.sha256") as mock_sha:
        mock_sha.return_value.hexdigest.return_value = "fp"
        get_or_create_client_tunnel("localhost", 1234, True, "pass")


@patch("usbip_gui.gui.client.tunnels.socket.create_connection")
@patch("usbip_gui.gui.client.tunnels.ssl.create_default_context")
@patch(
    "usbip_gui.gui.client.tunnels.QMessageBox.question",
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
    with patch(
        "usbip_gui.gui.client.tunnels.QMessageBox.critical"
    ) as mock_err:
        target, _port = get_or_create_client_tunnel(
            "localhost", 1234, True, ""
        )
        mock_err.assert_called_once()
        assert target == ""


@patch("usbip_gui.gui.client.tunnels.socket.create_connection")
@patch("usbip_gui.gui.client.tunnels.ssl.create_default_context")
@patch(
    "usbip_gui.gui.client.tunnels.QMessageBox.question",
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
    with patch(
        "usbip_gui.gui.client.tunnels.QMessageBox.critical"
    ) as mock_err:
        target, _port = get_or_create_client_tunnel(
            "localhost", 1234, True, "pass"
        )
        mock_err.assert_called_once()
        assert target == ""


@patch("usbip_gui.gui.client.tunnels.tunnel_state")
@patch(
    "usbip_gui.gui.client.tunnels.QMessageBox.question",
    return_value=QMessageBox.StandardButton.Yes,
)
@patch("usbip_gui.gui.client.tunnels.QMessageBox.critical")
@patch("usbip_gui.gui.client.tunnels.os.path.exists", return_value=False)
@patch("builtins.open", new_callable=mock_open)
def test_get_or_create_client_tunnel_kill(
    _mock_open: MagicMock,
    _mock_exists: MagicMock,
    _mock_critical: MagicMock,
    _mock_ask: MagicMock,
    mock_state: MagicMock,
):
    """Test get or create client tunnel kills old process."""

    mock_proc = MagicMock()
    mock_proc.poll.return_value = None
    mock_state.client_processes = {
        ("localhost", 1234): (1111, mock_proc, "old_pass")
    }
    with (
        patch("usbip_gui.gui.client.tunnels.subprocess.Popen"),
        patch("usbip_gui.gui.client.tunnels.threading.Thread"),
        patch("usbip_gui.gui.client.tunnels.time.sleep"),
        patch("usbip_gui.gui.client.tunnels.socket.create_connection"),
        patch(
            "usbip_gui.gui.client.tunnels.ssl.create_default_context"
        ) as mock_ctx,
    ):
        mock_wrap = mock_ctx.return_value.wrap_socket.return_value
        mock_ssock = mock_wrap.__enter__.return_value
        mock_ssock.getpeercert.return_value = b"cert"
        mock_ssock.recv.return_value = b"\x01"
        get_or_create_client_tunnel("localhost", 1234, True, "new_pass")
        mock_proc.kill.assert_called_once()


@patch("usbip_gui.gui.client.tab.list_remote_usb")
@patch("usbip_gui.gui.client.tab.list_attached_usb")
def test_client_ui_errors(mock_attached: MagicMock, mock_remote: MagicMock):
    """Test client ui errors."""

    mock_remote.return_value = [("a", "b", "c", "d")]
    mock_attached.return_value = [("a", 1, "b", "c", "d", "e")]
    parent = None
    client_tab = ClientTab(parent)

    with patch.object(
        client_tab.remote_listbox, "selectedItems", return_value=()
    ):
        with (
            patch(
                "usbip_gui.gui.client.tunnels.QMessageBox.critical"
            ) as mock_err,
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
            patch(
                "usbip_gui.gui.client.tunnels.QMessageBox.critical"
            ) as mock_err,
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
            patch(
                "usbip_gui.gui.client.tunnels.QMessageBox.critical"
            ) as mock_err,
            patch.object(
                client_tab.remote_ip_input, "text", return_value="localhost"
            ),
            patch.object(
                client_tab.remote_port_input, "text", return_value="1234"
            ),
        ):
            client_tab.attach_remote()
            mock_err.assert_called_once()

        with patch(
            "usbip_gui.gui.client.tunnels.QMessageBox.critical"
        ) as mock_err:
            client_tab.detach_remote()
            mock_err.assert_called_once()


def test_refresh_remote_with_attached():
    """Test refresh remote with devices already attached."""
    with patch("usbip_gui.gui.client.tab.list_remote_usb") as mock_remote:
        with patch(
            "usbip_gui.gui.client.tab.list_attached_usb"
        ) as mock_attached:
            mock_remote.return_value = [("1-1", "1234:5678", "Man", "Desc")]
            mock_attached.return_value = [
                ("localhost:1234", 1, "1-1", "1234:5678", "Man", "Desc"),
                ("localhost:4321", 2, "1-2", "8765:4321", "Man2", "Desc2"),
            ]
            tab = ClientTab(None)
            tab.remote_ip_input.setText("localhost")
            tab.remote_port_input.setText("1234")

            with patch.object(
                tab.remote_listbox, "addTopLevelItem"
            ) as mock_add:
                tab.refresh_remote()
                assert mock_add.call_count == 2

                with patch("usbip_gui.gui.client.sys.platform", "win32"):
                    with patch(
                        "usbip_gui.gui.client.tab.enrich_remote_device_item"
                    ) as mock_enrich:
                        tab.refresh_remote()
                        assert mock_enrich.call_count == 2


def test_attach_remote_already_attached():
    """Test attaching an already attached device."""
    tab = ClientTab(None)
    tab.remote_ip_input.setText("localhost")
    tab.remote_port_input.setText("1234")

    item = MagicMock()
    item.text.return_value = "Attached"
    with patch.object(
        tab.remote_listbox, "selectedItems", return_value=[item]
    ):
        with patch(
            "usbip_gui.gui.client.tab.QMessageBox.information"
        ) as mock_info:
            tab.attach_remote()
            mock_info.assert_called_once()


def test_detach_remote_not_attached():
    """Test detaching a device that is not attached."""
    tab = ClientTab(None)
    item = MagicMock()
    item.text.return_value = "Detached"
    with patch.object(
        tab.remote_listbox, "selectedItems", return_value=[item]
    ):
        with patch(
            "usbip_gui.gui.client.tab.QMessageBox.information"
        ) as mock_info:
            tab.detach_remote()
            mock_info.assert_called_once()


def test_detach_remote_no_local_port():
    """Test detaching a device without a local port."""
    tab = ClientTab(None)
    item = MagicMock()
    item.text.return_value = "Attached"
    item.data.return_value = -1
    with patch.object(
        tab.remote_listbox, "selectedItems", return_value=[item]
    ):
        with patch(
            "usbip_gui.gui.client.tunnels.QMessageBox.critical"
        ) as mock_crit:
            tab.detach_remote()
            mock_crit.assert_called_once()


def test_on_double_click_remote_attached():
    """Test double clicking an attached device."""
    tab = ClientTab(None)
    item = MagicMock()
    item.text.return_value = "Attached"
    with patch.object(tab, "detach_remote") as mock_detach:
        tab.on_double_click_remote(item, 0)
        mock_detach.assert_called_once()


@patch("usbip_gui.gui.client.operations.sys")
@patch("usbip_gui.gui.client.operations.get_or_create_client_tunnel")
@patch("usbip_gui.gui.client.operations._resolve_usbip_client_executable")
@patch("usbip_gui.gui.client.operations.run_elevated")
def test_attach_detach_remote_usb_win32(
    mock_run_elevated: MagicMock,
    mock_resolve_usbip: MagicMock,
    mock_tunnel: MagicMock,
    mock_sys: MagicMock,
):
    """Test attach/detach remote usb on win32 triggers UAC via run_elevated."""
    mock_sys.platform = "win32"
    detect = getattr(client_mod, "_detect_windows_attach_bus_option")
    detect.cache_clear()
    mock_run_elevated.return_value.returncode = 0
    mock_resolve_usbip.return_value = r"C:\Program Files\USBip\usbip.exe"
    mock_tunnel.return_value = ("127.0.0.1", 1234)

    attach_remote_usb("host", "1-1")
    attach_cmd = mock_run_elevated.call_args.args[0]
    assert attach_cmd[0] == r"C:\Program Files\USBip\usbip.exe"
    assert "--tcp-port" in attach_cmd
    assert "1234" in attach_cmd
    assert "attach" in attach_cmd
    assert "--remote=127.0.0.1" in attach_cmd
    assert any(arg in ("--busid=1-1", "--bus-id=1-1") for arg in attach_cmd)

    detach_remote_usb(1)
    mock_run_elevated.assert_called_with(
        [r"C:\Program Files\USBip\usbip.exe", "detach", "--port=1"]
    )


@patch("usbip_gui.gui.client.operations.sys")
@patch("usbip_gui.gui.client.operations.get_or_create_client_tunnel")
@patch("usbip_gui.gui.client.operations._resolve_usbip_client_executable")
@patch("usbip_gui.gui.client.operations.run_elevated")
@patch("usbip_gui.gui.client.subprocess.run")
def test_attach_remote_usb_win32_detects_bus_option(
    mock_run: MagicMock,
    mock_run_elevated: MagicMock,
    mock_resolve_usbip: MagicMock,
    mock_tunnel: MagicMock,
    mock_sys: MagicMock,
):
    """Test attach uses detected --bus-id option on win32."""
    mock_sys.platform = "win32"
    detect = getattr(client_mod, "_detect_windows_attach_bus_option")
    detect.cache_clear()
    mock_run.return_value = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="--bus-id", stderr=""
    )
    mock_run_elevated.return_value = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="", stderr=""
    )

    mock_resolve_usbip.return_value = r"C:\Program Files\USBip\usbip.exe"
    mock_tunnel.return_value = ("127.0.0.1", 1234)

    result = attach_remote_usb("host", "1-1", secure=True, password="pw")

    assert result.returncode == 0
    assert mock_run_elevated.call_count == 1
    cmd = mock_run_elevated.call_args_list[0].args[0]
    assert cmd[0].lower().endswith("usbip.exe")
    assert "--bus-id=1-1" in cmd


@patch("usbip_gui.gui.client.operations.sys")
@patch("usbip_gui.gui.client.operations.get_or_create_client_tunnel")
@patch("usbip_gui.gui.client.operations._resolve_usbip_client_executable")
@patch("usbip_gui.gui.client.operations.run_elevated")
def test_attach_remote_usb_win32_retries_same_exe(
    mock_run_elevated: MagicMock,
    mock_resolve_usbip: MagicMock,
    mock_tunnel: MagicMock,
    mock_sys: MagicMock,
):
    """Test secure attach retries once when command fails."""
    mock_sys.platform = "win32"
    with patch(
        "usbip_gui.gui.client.operations._detect_windows_attach_bus_option",
        return_value="--bus-id",
    ):
        mock_resolve_usbip.return_value = r"C:\Program Files\USBip\usbip.exe"
        mock_tunnel.return_value = ("127.0.0.1", 1234)

        first = subprocess.CompletedProcess(
            args=[], returncode=106, stdout="", stderr=""
        )
        second = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        mock_run_elevated.side_effect = [first, second]

        result = attach_remote_usb("host", "1-1", secure=True, password="pw")

    assert result.returncode == 0
    assert mock_run_elevated.call_count == 2
    first_cmd = mock_run_elevated.call_args_list[0].args[0]
    second_cmd = mock_run_elevated.call_args_list[1].args[0]
    assert first_cmd[0].lower().endswith("usbip.exe")
    assert second_cmd[0].lower().endswith("usbip.exe")
    assert "--bus-id=1-1" in first_cmd
    assert "--bus-id=1-1" in second_cmd


@patch("usbip_gui.gui.client.operations.sys")
@patch("usbip_gui.gui.client.operations.get_or_create_client_tunnel")
@patch("usbip_gui.gui.client.operations._resolve_usbip_client_executable")
@patch("usbip_gui.gui.client.operations.run_elevated")
@patch("usbip_gui.gui.client.subprocess.run")
def test_attach_remote_usb_win32_collects_diag_output(
    mock_run: MagicMock,
    mock_run_elevated: MagicMock,
    mock_resolve_usbip: MagicMock,
    mock_tunnel: MagicMock,
    mock_sys: MagicMock,
):
    """Test attach captures diagnostics from non-elevated run on failure."""
    mock_sys.platform = "win32"
    mock_resolve_usbip.return_value = r"C:\Program Files\USBip\usbip.exe"
    mock_tunnel.return_value = ("127.0.0.1", 1234)

    mock_run_elevated.return_value = subprocess.CompletedProcess(
        args=[], returncode=106, stdout="", stderr=""
    )
    mock_run.return_value = subprocess.CompletedProcess(
        args=[],
        returncode=106,
        stdout="",
        stderr="device not available",
    )

    result = attach_remote_usb("host", "1-1", secure=False, password="pw")

    assert result.returncode == 106
    assert "device not available" in result.stderr


@patch("usbip_gui.gui.client.operations.get_or_create_client_tunnel")
@patch("usbip_gui.gui.client.operations._resolve_usbip_client_executable")
@patch("usbip_gui.gui.client.operations.run_elevated")
def test_attach_remote_usb_secure_retry_target_missing_returns_initial(
    mock_run_elevated: MagicMock,
    mock_resolve_usbip: MagicMock,
    mock_tunnel: MagicMock,
):
    """Test secure attach returns initial failure when retry tunnel fails."""
    mock_resolve_usbip.return_value = "usbip"
    first = subprocess.CompletedProcess(
        args=[], returncode=106, stdout="", stderr=""
    )
    mock_run_elevated.return_value = first
    mock_tunnel.side_effect = [("127.0.0.1", 1234), ("", 0)]

    result = attach_remote_usb("host", "1-1", secure=True, password="pw")
    assert result is first


@patch("usbip_gui.gui.client.subprocess.run")
def test_detect_windows_attach_bus_option_caches(mock_run: MagicMock):
    """Test bus option detection caches after first probe."""
    mock_run.return_value = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="--bus-id", stderr=""
    )
    detect = getattr(client_mod, "_detect_windows_attach_bus_option")
    detect.cache_clear()
    first = detect("usbip.exe")
    second = detect("usbip.exe")

    assert first == "--bus-id"
    assert second == "--bus-id"
    mock_run.assert_called_once()


@patch("usbip_gui.gui.client.subprocess.run")
def test_detect_windows_attach_bus_option_prefers_busid(mock_run: MagicMock):
    """Test detection picks --busid when that's what help reports."""
    mock_run.return_value = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="--busid", stderr=""
    )
    detect = getattr(client_mod, "_detect_windows_attach_bus_option")
    detect.cache_clear()
    detected = detect("usbip.exe")
    assert detected == "--busid"


@patch("usbip_gui.gui.client.subprocess.run", side_effect=OSError("nope"))
def test_detect_windows_attach_bus_option_oserror_default(
    _mock_run: MagicMock,
):
    """Test detection safely defaults to --busid if probe fails."""
    detect = getattr(client_mod, "_detect_windows_attach_bus_option")
    detect.cache_clear()
    detected = detect("usbip.exe")
    assert detected == "--busid"


def test_secure_port_candidates_branches():
    """Test secure port candidate generation across platform branches."""
    secure_port_candidates = getattr(client_mod, "_secure_port_candidates")
    with patch("usbip_gui.gui.client.sys.platform", "win32"):
        assert secure_port_candidates(3240) == [3240, 3241]
        assert secure_port_candidates(3241) == [3241]
    with patch("usbip_gui.gui.client.sys.platform", "linux"):
        assert secure_port_candidates(3240) == [3240]


@patch("usbip_gui.gui.client.tunnels.tunnel_state")
def test_reset_client_tunnels_for_host(mock_state: MagicMock):
    """Test host-specific reset kills only matching running processes."""
    proc_running = MagicMock()
    proc_running.poll.return_value = None
    proc_stopped = MagicMock()
    proc_stopped.poll.return_value = 1
    proc_running_kill_error = MagicMock()
    proc_running_kill_error.poll.return_value = None
    proc_running_kill_error.kill.side_effect = OSError()

    mock_state.client_processes = {
        ("a", 1): (1111, proc_running, "pw"),
        ("a", 2): (2222, proc_running_kill_error, "pw"),
        ("b", 1): (3333, proc_stopped, "pw"),
    }

    reset_tunnels = getattr(client_mod, "_reset_client_tunnels_for_host")
    reset_tunnels("a")

    proc_running.kill.assert_called_once()
    proc_running_kill_error.kill.assert_called_once()
    assert ("a", 1) not in mock_state.client_processes
    assert ("a", 2) not in mock_state.client_processes
    assert ("b", 1) in mock_state.client_processes


@patch("usbip_gui.gui.client.operations.sys")
@patch("usbip_gui.gui.client.operations.get_or_create_client_tunnel")
@patch("usbip_gui.gui.client.operations._resolve_usbip_client_executable")
@patch("usbip_gui.gui.client.operations.run_elevated")
@patch("usbip_gui.gui.client.subprocess.run")
def test_attach_remote_usb_win32_diag_empty_keeps_original(
    mock_run: MagicMock,
    mock_run_elevated: MagicMock,
    mock_resolve_usbip: MagicMock,
    mock_tunnel: MagicMock,
    mock_sys: MagicMock,
):
    """Test diagnostics keeps original result when no output is captured."""
    mock_sys.platform = "win32"
    mock_resolve_usbip.return_value = r"C:\Program Files\USBip\usbip.exe"
    mock_tunnel.return_value = ("127.0.0.1", 1234)

    original = subprocess.CompletedProcess(
        args=["usbip"], returncode=106, stdout="", stderr="orig"
    )
    mock_run_elevated.return_value = original
    mock_run.return_value = subprocess.CompletedProcess(
        args=[], returncode=106, stdout="", stderr=""
    )

    with patch(
        "usbip_gui.gui.client.operations._detect_windows_attach_bus_option",
        return_value="--bus-id",
    ):
        result = attach_remote_usb("host", "1-1", secure=False, password="pw")

    assert result is original


@patch("usbip_gui.gui.client.operations.sys")
@patch("usbip_gui.gui.client.operations.get_or_create_client_tunnel")
@patch("usbip_gui.gui.client.operations._resolve_usbip_client_executable")
@patch("usbip_gui.gui.client.operations.run_elevated")
def test_attach_remote_usb_linux_uses_busid(
    mock_run_elevated: MagicMock,
    mock_resolve_usbip: MagicMock,
    mock_tunnel: MagicMock,
    mock_sys: MagicMock,
):
    """Test Linux attach path uses --busid argument form."""
    mock_sys.platform = "linux"
    mock_resolve_usbip.return_value = "usbip"
    mock_tunnel.return_value = ("127.0.0.1", 1234)
    mock_run_elevated.return_value = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="", stderr=""
    )

    result = attach_remote_usb("host", "1-1", secure=False, password="pw")

    assert result.returncode == 0
    cmd = mock_run_elevated.call_args.args[0]
    assert "--busid=1-1" in cmd


@patch("usbip_gui.gui.client.tab.attach_remote_usb")
@patch("usbip_gui.gui.client.tunnels.QMessageBox.critical")
def test_attach_remote_ui_error_details_with_hint(
    mock_critical: MagicMock, mock_attach: MagicMock
):
    """Test attach UI shows detailed error and 106 hint on failure."""
    mock_attach.return_value = subprocess.CompletedProcess(
        args=[], returncode=106, stdout="", stderr=""
    )
    tab = MagicMock()
    tab.remote_ip_input.text.return_value = "localhost"
    tab.remote_port_input.text.return_value = "3240"
    tab.remote_secure_checkbox.isChecked.return_value = True
    tab.remote_password_input.text.return_value = "pw"
    item = MagicMock()

    def _item_text(idx: int) -> str:
        return "1-1" if idx == 2 else "Detached"

    item.text.side_effect = _item_text
    tab.remote_listbox.selectedItems.return_value = [item]

    ClientTab.attach_remote(tab)

    assert mock_critical.called
    msg = mock_critical.call_args.args[2]
    assert "Failed to attach device 1-1" in msg
    assert "Exit code: 106" in msg
    assert "USB/IP driver/service is not ready" in msg
    tab.refresh_remote.assert_not_called()


@patch("usbip_gui.gui.client.tunnels.time.sleep")
@patch("usbip_gui.gui.client.tunnels.threading.Thread")
@patch("usbip_gui.gui.client.tunnels.subprocess.Popen")
@patch("usbip_gui.gui.client.tunnels.resolve_cloudflared_executable")
def test_get_or_create_cloudflared_client_tunnel(
    mock_resolve: MagicMock,
    mock_popen: MagicMock,
    mock_thread: MagicMock,
    mock_sleep: MagicMock,
):
    """Test get_or_create_cloudflared_client_tunnel lifecycle."""
    # 1. Existing active process returns cached port
    mock_active = MagicMock()
    mock_active.poll.return_value = None
    tunnel_state.cloudflared_client_processes["host1"] = (42000, mock_active)
    ip, port = get_or_create_cloudflared_client_tunnel("host1")
    assert ip == "127.0.0.1"
    assert port == 42000

    # 2. Existing dead process is cleaned up and new one spawned
    mock_active.poll.return_value = 1
    mock_resolve.return_value = "/usr/bin/cloudflared"
    mock_proc = MagicMock()
    mock_popen.return_value = mock_proc

    def execute_thread(
        target: Callable[[], object] | None = None,
        **_kwargs: object,
    ) -> MagicMock:
        thread_obj = MagicMock()
        if target:
            target()
        return thread_obj

    mock_thread.side_effect = execute_thread

    ip, port = get_or_create_cloudflared_client_tunnel(
        "host1", "/usr/bin/cloudflared"
    )
    assert ip == "127.0.0.1"
    mock_resolve.assert_called_with("/usr/bin/cloudflared")
    mock_popen.assert_called_once()
    mock_sleep.assert_called_with(1)
    # watch_cf_tunnel should have run and cleared it
    assert "host1" not in tunnel_state.cloudflared_client_processes

    # 3. Test with service tokens
    mock_popen.reset_mock()
    ip, port = get_or_create_cloudflared_client_tunnel(
        "host2",
        service_token_id="tok_id_123",
        service_token_secret="tok_sec_456",
    )
    assert ip == "127.0.0.1"
    popen_args = mock_popen.call_args[0][0]
    assert "--service-token-id" in popen_args
    assert "tok_id_123" in popen_args
    assert "--service-token-secret" in popen_args
    assert "tok_sec_456" in popen_args


@patch("usbip_gui.gui.client.subprocess.run")
@patch("usbip_gui.gui.client.operations.get_or_create_client_tunnel")
@patch(
    "usbip_gui.gui.client.operations.get_or_create_cloudflared_client_tunnel"
)
def test_list_remote_usb_cloudflared(
    mock_cf_tunnel: MagicMock,
    mock_direct_tunnel: MagicMock,
    mock_subproc_run: MagicMock,
):
    """Test list_remote_usb with cloudflared tunnel."""
    mock_subproc_run.return_value = MagicMock(stdout="")
    # Failure to establish cf tunnel
    mock_cf_tunnel.return_value = ("", 0)
    res = list_remote_usb("server", use_cloudflared=True)
    assert not res

    # Successful cf tunnel
    mock_cf_tunnel.return_value = ("127.0.0.1", 45000)
    mock_direct_tunnel.return_value = ("127.0.0.1", 45000)
    res = list_remote_usb(
        "default_host",
        use_cloudflared=True,
        cloudflared_hostname="usbip.maschmeyer.ca",
    )
    assert not res
    mock_cf_tunnel.assert_called_with(
        "usbip.maschmeyer.ca",
        "",
        service_token_id="",
        service_token_secret="",
    )


@patch("usbip_gui.gui.client.operations.run_elevated")
@patch("usbip_gui.gui.client.operations.get_or_create_client_tunnel")
@patch(
    "usbip_gui.gui.client.operations.get_or_create_cloudflared_client_tunnel"
)
def test_attach_remote_usb_cloudflared(
    mock_cf_tunnel: MagicMock,
    mock_direct_tunnel: MagicMock,
    mock_run: MagicMock,
):
    """Test attach_remote_usb with cloudflared tunnel."""
    mock_run.return_value = MagicMock(returncode=0)
    # Failure to establish cf tunnel
    mock_cf_tunnel.return_value = ("", 0)
    res = attach_remote_usb("server", "1-1", use_cloudflared=True)
    assert res.returncode == -1

    # Successful cf tunnel
    mock_cf_tunnel.return_value = ("127.0.0.1", 45000)
    mock_direct_tunnel.return_value = ("127.0.0.1", 45000)
    res = attach_remote_usb(
        "default_host",
        "1-1",
        use_cloudflared=True,
        cloudflared_hostname="usbip.maschmeyer.ca",
    )
    assert res.returncode == 0
    mock_cf_tunnel.assert_called_with(
        "usbip.maschmeyer.ca",
        "",
        service_token_id="",
        service_token_secret="",
    )


@patch("usbip_gui.gui.client.tab.set_selected_site_name")
@patch("usbip_gui.gui.client.tab.QMessageBox.warning")
def test_client_tab_site_selection_and_cf(
    _mock_warning: MagicMock, mock_set: MagicMock
):
    """Test ClientTab site combo, selection, and cf settings."""
    with patch("usbip_gui.gui.client.tab.list_attached_usb", return_value=[]):
        tab = ClientTab(None)

    mock_sites = [
        {
            "name": "Direct Client",
            "connection_type": "direct",
            "host": "192.168.1.50",
            "port": 3240,
            "secure": False,
            "password": "",
        },
        {
            "name": "Cloudflare Client",
            "connection_type": "cloudflared",
            "cloudflared_hostname": "usbip.maschmeyer.ca",
            "cloudflared_path": "/opt/cf",
            "cloudflared_token_id": "tok_id",
            "cloudflared_token_secret": "tok_sec",
            "port": 3240,
            "secure": True,
            "password": "pass",
        },
    ]

    with (
        patch("usbip_gui.gui.client.tab.load_sites", return_value=mock_sites),
        patch(
            "usbip_gui.gui.client.tab.get_selected_site_name",
            return_value="Cloudflare Client",
        ),
    ):
        tab.populate_site_combo()
        assert tab.remote_site_combo.count() == 3
        assert tab.remote_site_combo.currentText() == "Cloudflare Client"

    # Test on_sites_updated
    with patch.object(tab, "populate_site_combo") as mock_pop:
        tab.on_sites_updated("server")
        mock_pop.assert_not_called()
        tab.on_sites_updated("client")
        mock_pop.assert_called_once()

    # Test on_site_selected with empty site
    tab.remote_site_combo.setCurrentIndex(0)
    tab.on_site_selected(0)
    mock_set.assert_called_with("client", "")

    # Test on_site_selected with non-existent site
    tab.remote_site_combo.setCurrentIndex(1)
    with patch("usbip_gui.gui.client.tab.get_site", return_value=None):
        tab.on_site_selected(1)

    # Test on_site_selected with direct site
    direct_site = mock_sites[0]
    with patch("usbip_gui.gui.client.tab.get_site", return_value=direct_site):
        tab.on_site_selected(1)
        assert tab.remote_ip_input.text() == "192.168.1.50"

    # Test on_site_selected with cloudflared site
    cf_site = mock_sites[1]
    with patch("usbip_gui.gui.client.tab.get_site", return_value=cf_site):
        tab.remote_site_combo.setCurrentIndex(2)
        tab.on_site_selected(2)
        assert tab.remote_ip_input.text() == "usbip.maschmeyer.ca"
        assert tab.remote_port_input.text() == "3240"
        assert tab.remote_secure_checkbox.isChecked() is True
        assert tab.remote_password_input.text() == "pass"

    # Test get_active_cf_settings
    with patch("usbip_gui.gui.client.tab.get_site", return_value=cf_site):
        use_cf, host, path, tok_id, tok_sec = tab.get_active_cf_settings()
        assert use_cf is True
        assert host == "usbip.maschmeyer.ca"
        assert path == "/opt/cf"
        assert tok_id == "tok_id"
        assert tok_sec == "tok_sec"

    with patch("usbip_gui.gui.client.tab.get_site", return_value=direct_site):
        use_cf, host, path, tok_id, tok_sec = tab.get_active_cf_settings()
        assert use_cf is False
        assert host == ""
        assert path == ""
        assert tok_id == ""
        assert tok_sec == ""

    # Test connect_site
    with patch.object(tab, "refresh_remote") as mock_refresh:
        tab.connect_site()
        mock_refresh.assert_called_once()

    # Test encrypted password sets empty string in on_site_selected
    enc_site = {
        "name": "Encrypted Site",
        "connection_type": "cloudflared",
        "cloudflared_hostname": "test.host",
        "cloudflared_token_id": {"enc": "v1"},
        "cloudflared_token_secret": {"enc": "v1"},
        "port": 3240,
        "password": {"enc": "v1"},
    }
    with patch("usbip_gui.gui.client.tab.get_site", return_value=enc_site):
        tab.on_site_selected(2)
        assert tab.remote_password_input.text() == ""
        use_cf, host, path, tok_id, tok_sec = tab.get_active_cf_settings()
        assert use_cf is True
        assert tok_id == ""
        assert tok_sec == ""

    # Test refresh_remote aborts if unlock cancelled
    with patch.object(
        tab.remote_site_combo, "currentData", return_value="Encrypted Site"
    ):
        with patch("usbip_gui.gui.client.tab.get_site", return_value=enc_site):
            with patch(
                "usbip_gui.gui.client.tab.site_requires_unlock",
                return_value=True,
            ):
                with patch(
                    "usbip_gui.gui.client.tab.ensure_unlocked",
                    return_value=False,
                ):
                    with patch(
                        "usbip_gui.gui.client.tab.list_remote_usb"
                    ) as mock_list:
                        tab.refresh_remote()
                        mock_list.assert_not_called()

                # Test refresh_remote succeeds if unlocked
                with patch(
                    "usbip_gui.gui.client.tab.ensure_unlocked",
                    return_value=True,
                ):
                    with patch.object(tab, "on_site_selected") as mock_sel:
                        with (
                            patch(
                                "usbip_gui.gui.client.tab.list_remote_usb"
                            ) as mock_list,
                            patch(
                                "usbip_gui.gui.client.tab.list_attached_usb",
                                return_value=[],
                            ),
                        ):
                            tab.refresh_remote()
                            mock_sel.assert_called_once()
                            mock_list.assert_called_once()


@patch("usbip_gui.gui.client.tab.list_attached_usb", return_value=[])
@patch("usbip_gui.gui.client.tab.list_remote_usb")
@patch("usbip_gui.gui.client.tunnels.QMessageBox.critical")
def test_refresh_remote_cloudflared_validation_and_call(
    mock_critical: MagicMock,
    mock_list: MagicMock,
    _mock_attached: MagicMock,
):
    """Test refresh_remote validation and invocation with cloudflared."""
    tab = MagicMock()
    tab.remote_ip_input.text.return_value = "default_ip"
    tab.remote_port_input.text.return_value = "3240"
    tab.remote_secure_checkbox.isChecked.return_value = False
    tab.remote_password_input.text.return_value = ""

    # Missing cf hostname
    tab.get_active_cf_settings.return_value = (
        True,
        "",
        "",
        "",
        "",
    )
    ClientTab.refresh_remote(tab)
    mock_critical.assert_called_once()
    mock_list.assert_not_called()

    # Valid cf hostname
    mock_critical.reset_mock()
    tab.get_active_cf_settings.return_value = (
        True,
        "usbip.maschmeyer.ca",
        "/cf/path",
        "tok_id",
        "tok_sec",
    )
    mock_list.return_value = []
    ClientTab.refresh_remote(tab)
    mock_critical.assert_not_called()
    mock_list.assert_called_once_with(
        "default_ip",
        3240,
        False,
        "",
        use_cloudflared=True,
        cloudflared_hostname="usbip.maschmeyer.ca",
        cloudflared_path="/cf/path",
        service_token_id="tok_id",
        service_token_secret="tok_sec",
    )


@patch("usbip_gui.gui.client.tunnels.time.sleep")
@patch("usbip_gui.gui.client.tab.attach_remote_usb")
@patch("usbip_gui.gui.client.tunnels.QMessageBox.critical")
def test_attach_remote_cloudflared_validation_and_call(
    mock_critical: MagicMock,
    mock_attach: MagicMock,
    _mock_sleep: MagicMock,
):
    """Test attach_remote validation and invocation with cloudflared."""
    tab = MagicMock()
    tab.remote_ip_input.text.return_value = "default_ip"
    tab.remote_port_input.text.return_value = "3240"
    tab.remote_secure_checkbox.isChecked.return_value = False
    tab.remote_password_input.text.return_value = ""
    item = MagicMock()

    def item_text(idx: int) -> str:
        return "1-1" if idx == 2 else "Detached"

    item.text.side_effect = item_text
    tab.remote_listbox.selectedItems.return_value = [item]

    # Missing cf hostname
    tab.get_active_cf_settings.return_value = (
        True,
        "",
        "",
        "",
        "",
    )
    ClientTab.attach_remote(tab)
    mock_critical.assert_called_once()
    mock_attach.assert_not_called()

    # Valid cf hostname
    mock_critical.reset_mock()
    tab.get_active_cf_settings.return_value = (
        True,
        "usbip.maschmeyer.ca",
        "/cf/path",
        "tok_id",
        "tok_sec",
    )
    mock_attach.return_value = MagicMock(returncode=0)
    ClientTab.attach_remote(tab)
    mock_critical.assert_not_called()
    mock_attach.assert_called_once_with(
        "default_ip",
        "1-1",
        3240,
        False,
        "",
        use_cloudflared=True,
        cloudflared_hostname="usbip.maschmeyer.ca",
        cloudflared_path="/cf/path",
        service_token_id="tok_id",
        service_token_secret="tok_sec",
    )
