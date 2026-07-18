"""Tests for the client tab."""

# pylint: disable=duplicate-code, too-many-lines

import subprocess
from pathlib import PurePosixPath
from types import TracebackType
from typing import Literal, Type

from unittest.mock import MagicMock, mock_open, patch
from PyQt6.QtWidgets import QMessageBox
import usbip_gui.gui.client as client_mod

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


@patch("usbip_gui.gui.client.sys")
@patch("usbip_gui.gui.client.shutil.which")
def test_resolve_usbip_client_executable_which_match(
    mock_which: MagicMock, mock_sys: MagicMock
):
    """Test win32 executable resolution uses PATH match when present."""
    mock_sys.platform = "win32"
    mock_which.side_effect = [r"C:\USBip\usbip.exe", None]
    resolve_exe = client_mod.__dict__["_resolve_usbip_client_executable"]
    assert resolve_exe() == r"C:\USBip\usbip.exe"


@patch("usbip_gui.gui.client.sys")
@patch("usbip_gui.gui.client.shutil.which", return_value=None)
@patch("usbip_gui.gui.client.Path.exists")
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


@patch("usbip_gui.gui.client.sys")
@patch("usbip_gui.gui.client.shutil.which", return_value=None)
@patch("usbip_gui.gui.client.Path.exists", return_value=False)
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


@patch("usbip_gui.gui.client.sys")
@patch("usbip_gui.gui.client.shutil.which", return_value=None)
@patch("usbip_gui.gui.client.Path.exists", return_value=False)
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
@patch("usbip_gui.gui.client._resolve_usbip_client_executable")
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


@patch("usbip_gui.gui.client.get_or_create_client_tunnel")
@patch("usbip_gui.gui.client._resolve_usbip_client_executable")
@patch("usbip_gui.gui.client.run_elevated")
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


@patch("usbip_gui.gui.client._resolve_usbip_client_executable")
@patch("usbip_gui.gui.client.run_elevated")
def test_detach_remote_usb(
    mock_run_elevated: MagicMock, mock_resolve_usbip: MagicMock
):
    """Test detach remote usb."""
    mock_resolve_usbip.return_value = "usbip"
    detach_remote_usb(1)
    mock_run_elevated.assert_called_with(["usbip", "detach", "--port=1"])


@patch("usbip_gui.gui.client.QMessageBox.warning")
def test_check_secure_warning(mock_warning: MagicMock):
    """Test check secure warning."""
    ClientTab.check_secure_warning(MagicMock(), 0)
    mock_warning.assert_called_once()


@patch("usbip_gui.gui.client.SortableTreeWidgetItem")
@patch("usbip_gui.gui.client.list_remote_usb")
@patch("usbip_gui.gui.client.list_attached_usb")
def test_refresh_remote(
    mock_attached_list: MagicMock,
    mock_remote_list: MagicMock,
    mock_item: MagicMock,
):
    """Test refresh remote."""
    mock_remote_list.return_value = [("1-1", "Man", "Desc")]
    mock_attached_list.return_value = []
    tab = MagicMock()
    tab.remote_ip_input.text.return_value = "localhost"
    tab.remote_port_input.text.return_value = "1234"
    ClientTab.refresh_remote(tab)
    tab.remote_listbox.clear.assert_called_once()
    mock_item.assert_called_once_with(
        tab.remote_listbox,
        ["localhost", "1234", "1-1", "Detached", "Man", "Desc"],
    )


@patch("usbip_gui.gui.client.QMessageBox.critical")
@patch("usbip_gui.gui.client.list_remote_usb")
@patch("usbip_gui.gui.client.list_attached_usb")
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


@patch("usbip_gui.gui.client.time.sleep")
@patch("usbip_gui.gui.client.detach_remote_usb")
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


@patch("usbip_gui.gui.client.time.sleep")
@patch("usbip_gui.gui.client.threading.Thread")
@patch("usbip_gui.gui.client.subprocess.Popen")
@patch("usbip_gui.gui.client.tunnel_state")
@patch("usbip_gui.gui.client.socket.create_connection")
@patch("usbip_gui.gui.client.ssl.create_default_context")
@patch(
    "usbip_gui.gui.client.QMessageBox.question",
    return_value=QMessageBox.StandardButton.Yes,
)
@patch("usbip_gui.gui.client.os.path.exists", return_value=False)
@patch("usbip_gui.gui.client.os.makedirs")
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


@patch("usbip_gui.gui.client.socket.create_connection")
@patch("usbip_gui.gui.client.ssl.create_default_context")
@patch("usbip_gui.gui.client.QMessageBox.critical")
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


@patch("usbip_gui.gui.client.socket.create_connection")
@patch("usbip_gui.gui.client.ssl.create_default_context")
@patch(
    "usbip_gui.gui.client.QMessageBox.question",
    return_value=QMessageBox.StandardButton.Yes,
)
@patch("usbip_gui.gui.client.QMessageBox.critical")
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
        patch("usbip_gui.gui.client.os.path.exists", return_value=False),
        patch("builtins.open", mock_open()),
        patch(
            "usbip_gui.gui.client._secure_port_candidates",
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
@patch("usbip_gui.gui.client.QMessageBox.critical")
@patch("usbip_gui.gui.client.os.path.exists", return_value=False)
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

    with patch.object(
        client_tab.remote_listbox, "selectedItems", return_value=()
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


def test_refresh_remote_with_attached():
    """Test refresh remote with devices already attached."""
    with patch("usbip_gui.gui.client.list_remote_usb") as mock_remote:
        with patch("usbip_gui.gui.client.list_attached_usb") as mock_attached:
            mock_remote.return_value = [("1-1", "Man", "Desc")]
            mock_attached.return_value = [
                ("localhost:1234", 1, "1-1", "Man", "Desc"),
                ("localhost:4321", 2, "1-2", "Man2", "Desc2"),
            ]
            tab = ClientTab(None)
            tab.remote_ip_input.setText("localhost")
            tab.remote_port_input.setText("1234")

            with patch.object(
                tab.remote_listbox, "addTopLevelItem"
            ) as mock_add:
                tab.refresh_remote()
                assert mock_add.call_count == 2


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
            "usbip_gui.gui.client.QMessageBox.information"
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
            "usbip_gui.gui.client.QMessageBox.information"
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
        with patch("usbip_gui.gui.client.QMessageBox.critical") as mock_crit:
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


@patch("usbip_gui.gui.client.sys")
@patch("usbip_gui.gui.client.get_or_create_client_tunnel")
@patch("usbip_gui.gui.client._resolve_usbip_client_executable")
@patch("usbip_gui.gui.client.run_elevated")
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


@patch("usbip_gui.gui.client.sys")
@patch("usbip_gui.gui.client.get_or_create_client_tunnel")
@patch("usbip_gui.gui.client._resolve_usbip_client_executable")
@patch("usbip_gui.gui.client.run_elevated")
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


@patch("usbip_gui.gui.client.sys")
@patch("usbip_gui.gui.client.get_or_create_client_tunnel")
@patch("usbip_gui.gui.client._resolve_usbip_client_executable")
@patch("usbip_gui.gui.client.run_elevated")
def test_attach_remote_usb_win32_retries_same_exe(
    mock_run_elevated: MagicMock,
    mock_resolve_usbip: MagicMock,
    mock_tunnel: MagicMock,
    mock_sys: MagicMock,
):
    """Test secure attach retries once when command fails."""
    mock_sys.platform = "win32"
    with patch(
        "usbip_gui.gui.client._detect_windows_attach_bus_option",
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


@patch("usbip_gui.gui.client.sys")
@patch("usbip_gui.gui.client.get_or_create_client_tunnel")
@patch("usbip_gui.gui.client._resolve_usbip_client_executable")
@patch("usbip_gui.gui.client.run_elevated")
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


@patch("usbip_gui.gui.client.get_or_create_client_tunnel")
@patch("usbip_gui.gui.client._resolve_usbip_client_executable")
@patch("usbip_gui.gui.client.run_elevated")
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


@patch("usbip_gui.gui.client.tunnel_state")
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


@patch("usbip_gui.gui.client.sys")
@patch("usbip_gui.gui.client.get_or_create_client_tunnel")
@patch("usbip_gui.gui.client._resolve_usbip_client_executable")
@patch("usbip_gui.gui.client.run_elevated")
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
        "usbip_gui.gui.client._detect_windows_attach_bus_option",
        return_value="--bus-id",
    ):
        result = attach_remote_usb("host", "1-1", secure=False, password="pw")

    assert result is original


@patch("usbip_gui.gui.client.sys")
@patch("usbip_gui.gui.client.get_or_create_client_tunnel")
@patch("usbip_gui.gui.client._resolve_usbip_client_executable")
@patch("usbip_gui.gui.client.run_elevated")
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


@patch("usbip_gui.gui.client.attach_remote_usb")
@patch("usbip_gui.gui.client.QMessageBox.critical")
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
