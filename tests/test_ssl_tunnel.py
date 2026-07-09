"""Tests for the ssl_tunnel module."""

import runpy
import sys
import os
from unittest.mock import patch, MagicMock
from usbip_gui.ssl_tunnel import (
    get_cert_fingerprint,
    generate_self_signed_cert,
    recv_exact,
    get_cert_paths,
    server_handle_connection,
    client_handle_connection,
    forward,
    start_server,
    start_client,
    main,
)


def test_get_cert_fingerprint_missing_file():
    """Test getting fingerprint of a missing file returns a fallback."""
    fingerprint = get_cert_fingerprint("/non/existent/path/to/cert.pem")
    assert fingerprint == "No certificate"


@patch("usbip_gui.ssl_tunnel.os.path.exists")
@patch("builtins.open", new_callable=MagicMock)
@patch("usbip_gui.ssl_tunnel.ssl.PEM_cert_to_DER_cert")
def test_get_cert_fingerprint_existing(
    mock_pem: MagicMock, mock_open: MagicMock, mock_exists: MagicMock
):
    """Test getting fingerprint of existing certificate."""
    mock_exists.return_value = True
    mock_open.return_value.__enter__.return_value.read.return_value = (
        "pem_data"
    )
    mock_pem.return_value = b"der_data"

    fp = get_cert_fingerprint("/path/to/cert.pem")
    assert fp != "No certificate"
    mock_open.assert_called_once_with(
        "/path/to/cert.pem", "r", encoding="utf-8"
    )


@patch("usbip_gui.ssl_tunnel.subprocess.run")
def test_generate_self_signed_cert(mock_run: MagicMock):
    """Test generating a self-signed cert."""
    generate_self_signed_cert("/path/to/cert", "/path/to/key")
    mock_run.assert_called_once()


def test_recv_exact():
    """Test recv_exact function."""
    mock_sock = MagicMock()
    mock_sock.recv.side_effect = [b"he", b"ll", b"o"]
    data = recv_exact(mock_sock, 5)
    assert data == b"hello"


@patch.dict("os.environ", {}, clear=True)
@patch("usbip_gui.ssl_tunnel.os.path.expanduser")
@patch("usbip_gui.ssl_tunnel.os.makedirs")
def test_get_cert_paths(mock_makedirs: MagicMock, mock_expanduser: MagicMock):
    """Test getting config paths."""
    mock_expanduser.return_value = "/mock/dir"
    cert, key = get_cert_paths()
    mock_makedirs.assert_called_once_with("/mock/dir/usbip-gui", exist_ok=True)
    assert cert == "/mock/dir/usbip-gui/server.crt"
    assert key == "/mock/dir/usbip-gui/server.key"


@patch("usbip_gui.ssl_tunnel.socket.socket")
@patch("usbip_gui.ssl_tunnel.forward")
def test_server_handle_connection(
    mock_forward: MagicMock, _mock_socket: MagicMock
):
    """Test server handling client connection with correct password."""
    client = MagicMock()
    client.recv.side_effect = [b"\x00\x00\x00\x04", b"pass"]
    server_handle_connection(client, "127.0.0.1", 1234, "pass")
    mock_forward.assert_called_once()
    client.sendall.assert_called_with(b"\x01")


@patch("usbip_gui.ssl_tunnel.socket.socket")
@patch("usbip_gui.ssl_tunnel.forward")
def test_server_handle_connection_bad_auth(
    mock_forward: MagicMock, _mock_socket: MagicMock
):
    """Test server handling client connection with bad auth."""
    client = MagicMock()
    client.recv.side_effect = [b"\x00\x00\x00\x04", b"badp"]
    server_handle_connection(client, "127.0.0.1", 1234, "pass")
    mock_forward.assert_not_called()
    client.sendall.assert_called_with(b"\x00")


@patch("usbip_gui.ssl_tunnel.socket.socket")
@patch("usbip_gui.ssl_tunnel.forward")
def test_client_handle_connection(
    mock_forward: MagicMock, _mock_socket: MagicMock
):
    """Test client connecting to remote server."""
    local_sock = MagicMock()
    context = MagicMock()
    ssl_sock = context.wrap_socket.return_value
    ssl_sock.recv.return_value = b"\x01"
    client_handle_connection(local_sock, ("127.0.0.1", 1234), "pass", context)
    ssl_sock.connect.assert_called_once_with(("127.0.0.1", 1234))
    mock_forward.assert_called_once_with(local_sock, ssl_sock)


@patch("usbip_gui.ssl_tunnel.threading.Thread")
def test_forward(mock_thread: MagicMock):
    """Test forward function threading."""
    sock1 = MagicMock()
    sock2 = MagicMock()
    forward(sock1, sock2)
    assert mock_thread.call_count == 2
    mock_thread.return_value.start.assert_called()


@patch("usbip_gui.ssl_tunnel.get_cert_paths", return_value=("cert", "key"))
@patch("usbip_gui.ssl_tunnel.os.path.exists", return_value=True)
@patch("usbip_gui.ssl_tunnel.ssl.create_default_context")
@patch("usbip_gui.ssl_tunnel.socket.socket")
@patch("usbip_gui.ssl_tunnel.threading.Thread")
def test_start_server(
    _mock_thread: MagicMock,
    mock_sock: MagicMock,
    mock_ctx: MagicMock,
    _mock_exists: MagicMock,
    _mock_paths: MagicMock,
):
    """Test start server loop."""
    server_sock = mock_sock.return_value
    # break out of while True loop by raising OSError
    server_sock.accept.side_effect = [
        (MagicMock(), MagicMock()),
        OSError("break"),
    ]
    start_server(1234, 5678, "pass")
    mock_ctx.assert_called_once()
    server_sock.bind.assert_called_once_with(("127.0.0.1", 1234))
    server_sock.listen.assert_called_once()


@patch("usbip_gui.ssl_tunnel.ssl.create_default_context")
@patch("usbip_gui.ssl_tunnel.socket.socket")
@patch("usbip_gui.ssl_tunnel.threading.Thread")
def test_start_client(
    _mock_thread: MagicMock, mock_sock: MagicMock, mock_ctx: MagicMock
):
    """Test start client loop."""
    client_sock = mock_sock.return_value
    # break out of while True loop by raising OSError
    client_sock.accept.side_effect = OSError("break")
    try:
        start_client(1234, "127.0.0.1", 5678, "pass")
    except OSError:
        pass
    mock_ctx.assert_called_once()
    client_sock.bind.assert_called_once_with(("127.0.0.1", 1234))


@patch("usbip_gui.ssl_tunnel.start_server")
def test_main_server(mock_start: MagicMock):
    """Test execution as a script for server mode."""
    args = [
        "ssl_tunnel.py",
        "server",
        "--listen-port",
        "1234",
        "--target-port",
        "5678",
        "--password",
        "test",
    ]
    with patch.object(sys, "argv", args):
        main()
        mock_start.assert_called_once_with(1234, 5678, "test", "127.0.0.1")


@patch("usbip_gui.ssl_tunnel.start_client")
def test_main_client(mock_start: MagicMock):
    """Test execution as a script for client mode."""
    args = [
        "ssl_tunnel.py",
        "client",
        "--listen-port",
        "1234",
        "--remote-host",
        "host",
        "--remote-port",
        "5678",
        "--password",
        "test",
    ]
    with patch.object(sys, "argv", args):
        main()
        mock_start.assert_called_once_with(1234, "host", 5678, "test", "")


def test_recv_exact_incomplete():
    """Test incomplete read."""
    mock_sock = MagicMock()
    mock_sock.recv.side_effect = [b"a", b""]
    data = recv_exact(mock_sock, 4)
    assert data == b""


@patch("usbip_gui.ssl_tunnel.recv_exact")
def test_server_handle_connection_short_read(mock_recv: MagicMock):
    """Test server handle with incomplete length."""
    client = MagicMock()
    mock_recv.return_value = b"\x00\x01"  # less than 4
    server_handle_connection(client, "127.0.0.1", 1234, "pass")
    client.sendall.assert_not_called()


@patch("usbip_gui.ssl_tunnel.recv_exact")
def test_server_handle_connection_oserror(mock_recv: MagicMock):
    """Test server handle OSError."""
    client = MagicMock()
    mock_recv.side_effect = OSError(1, "EPERM")
    server_handle_connection(client, "127.0.0.1", 1234, "pass")
    client.sendall.assert_not_called()


@patch("usbip_gui.ssl_tunnel.recv_exact")
def test_server_handle_connection_sendall_oserror(mock_recv: MagicMock):
    """Test server handle OSError during sendall."""
    client = MagicMock()
    mock_recv.side_effect = [b"\x00\x00\x00\x04", b"badp"]
    client.sendall.side_effect = OSError()
    server_handle_connection(client, "127.0.0.1", 1234, "pass")
    client.sendall.assert_called_once()


@patch("usbip_gui.ssl_tunnel.socket.socket")
@patch("usbip_gui.ssl_tunnel.forward")
def test_client_handle_connection_no_cert(
    mock_forward: MagicMock, _mock_sock: MagicMock
):
    """Test client handle no cert."""
    local_sock = MagicMock()
    context = MagicMock()
    ssl_sock = context.wrap_socket.return_value
    ssl_sock.getpeercert.return_value = None
    client_handle_connection(
        local_sock, ("127.0.0.1", 1234), "pass", context, "expected"
    )
    mock_forward.assert_not_called()


@patch("usbip_gui.ssl_tunnel.socket.socket")
@patch("usbip_gui.ssl_tunnel.forward")
def test_client_handle_connection_mismatch_cert(
    mock_forward: MagicMock, _mock_sock: MagicMock
):
    """Test client handle cert mismatch."""
    local_sock = MagicMock()
    context = MagicMock()
    ssl_sock = context.wrap_socket.return_value
    ssl_sock.getpeercert.return_value = b"cert"
    client_handle_connection(
        local_sock, ("127.0.0.1", 1234), "pass", context, "expected"
    )
    mock_forward.assert_not_called()


@patch("usbip_gui.ssl_tunnel.socket.socket")
@patch("usbip_gui.ssl_tunnel.forward")
def test_client_handle_connection_oserror(
    mock_forward: MagicMock, _mock_sock: MagicMock
):
    """Test client handle OSError."""
    local_sock = MagicMock()
    context = MagicMock()
    ssl_sock = context.wrap_socket.return_value
    ssl_sock.connect.side_effect = OSError(1, "EPERM")
    client_handle_connection(local_sock, ("127.0.0.1", 1234), "pass", context)
    mock_forward.assert_not_called()


@patch("usbip_gui.ssl_tunnel.recv_exact")
def test_server_handle_connection_close_oserror(mock_recv: MagicMock):
    """Test server handle OSError on close."""
    client = MagicMock()
    client.close.side_effect = OSError()
    mock_recv.side_effect = OSError(1, "EPERM")
    server_handle_connection(client, "127.0.0.1", 1234, "pass")


@patch("usbip_gui.ssl_tunnel.socket.socket")
@patch("usbip_gui.ssl_tunnel.forward")
def test_client_handle_connection_auth_fail(
    mock_forward: MagicMock, _mock_sock: MagicMock
):
    """Test client handle auth fail."""
    local_sock = MagicMock()
    context = MagicMock()
    ssl_sock = context.wrap_socket.return_value
    ssl_sock.recv.return_value = b"\x00"
    client_handle_connection(local_sock, ("127.0.0.1", 1234), "pass", context)
    mock_forward.assert_not_called()


@patch("usbip_gui.ssl_tunnel.socket.socket")
@patch("usbip_gui.ssl_tunnel.forward")
def test_client_handle_connection_close_oserror(
    mock_forward: MagicMock, _mock_sock: MagicMock
):
    """Test client handle OSError on close."""
    local_sock = MagicMock()
    local_sock.close.side_effect = OSError()
    context = MagicMock()
    ssl_sock = context.wrap_socket.return_value
    ssl_sock.connect.side_effect = OSError(1, "EPERM")
    client_handle_connection(local_sock, ("127.0.0.1", 1234), "pass", context)
    mock_forward.assert_not_called()


@patch("usbip_gui.ssl_tunnel.os.path.exists", return_value=False)
@patch("usbip_gui.ssl_tunnel.generate_self_signed_cert")
@patch("usbip_gui.ssl_tunnel.socket.socket")
@patch("usbip_gui.ssl_tunnel.ssl.create_default_context")
def test_start_server_gen_cert(
    _mock_ctx: MagicMock,
    mock_sock: MagicMock,
    mock_gen: MagicMock,
    _mock_exists: MagicMock,
):
    """Test start server generating cert."""
    mock_sock.return_value.accept.side_effect = KeyboardInterrupt()
    try:
        start_server(1234, 5678, "pass")
    except KeyboardInterrupt:
        pass
    mock_gen.assert_called_once()


def test_forward_exceptions():
    """Test forward handles OSErrors gracefully."""
    sock1 = MagicMock()
    sock2 = MagicMock()
    sock1.recv.side_effect = [b"data", OSError(1, "EPERM")]
    sock2.recv.side_effect = OSError(1, "EPERM")
    sock1.close.side_effect = OSError(1, "EPERM")
    sock2.close.side_effect = OSError(1, "EPERM")
    sock1.shutdown.side_effect = OSError(1, "EPERM")
    sock2.shutdown.side_effect = OSError(1, "EPERM")

    forward(sock1, sock2)
    sock1.close.assert_called_once()
    sock2.close.assert_called_once()


@patch("usbip_gui.ssl_tunnel.os.path.exists", return_value=True)
@patch("usbip_gui.ssl_tunnel.socket.socket")
@patch("usbip_gui.ssl_tunnel.ssl.create_default_context")
def test_start_server_accept_oserror(
    _mock_ctx: MagicMock, mock_sock: MagicMock, _mock_exists: MagicMock
):
    """Test start server accept loop OSError."""
    mock_sock.return_value.accept.side_effect = [
        OSError(1, "EPERM"),
        KeyboardInterrupt(),
    ]
    try:
        start_server(1234, 5678, "pass")
    except KeyboardInterrupt:
        pass


@patch("usbip_gui.ssl_tunnel.socket.socket")
def test_start_server_general_oserror(mock_sock: MagicMock):
    """Test start server general OSError."""
    mock_sock.return_value.bind.side_effect = OSError(1, "EPERM")
    start_server(1234, 5678, "pass")  # Should catch and not crash


@patch("usbip_gui.ssl_tunnel.socket.socket")
@patch("usbip_gui.ssl_tunnel.ssl.create_default_context")
def test_start_client_loop(_mock_ctx: MagicMock, mock_sock: MagicMock):
    """Test start client loop."""
    mock_sock.return_value.accept.side_effect = [
        (MagicMock(), "addr"),
        KeyboardInterrupt(),
    ]
    try:
        start_client(1234, "remote", 5678, "pass")
    except KeyboardInterrupt:
        pass


@patch("usbip_gui.ssl_tunnel.socket.socket")
def test_forward_eof(_mock_sock: MagicMock):
    """Test forward EOF."""
    sock1 = MagicMock()
    sock2 = MagicMock()
    sock1.recv.return_value = b""
    sock2.recv.return_value = b""
    forward(sock1, sock2)


@patch("usbip_gui.ssl_tunnel.os.path.exists", return_value=True)
@patch("usbip_gui.ssl_tunnel.socket.socket")
@patch("usbip_gui.ssl_tunnel.ssl.create_default_context")
def test_start_server_accept_wrap_oserror(
    mock_ctx: MagicMock, mock_sock: MagicMock, _mock_exists: MagicMock
):
    """Test accept wrap oserror."""
    mock_sock.return_value.accept.side_effect = [
        (MagicMock(), "addr"),
        KeyboardInterrupt(),
    ]
    mock_ctx.return_value.wrap_socket.side_effect = OSError()
    try:
        start_server(1234, 5678, "pass")
    except KeyboardInterrupt:
        pass


def test_main_name():
    """Test dunder main."""

    with patch("argparse.ArgumentParser.parse_args", side_effect=SystemExit):
        try:
            runpy.run_path("usbip_gui/ssl_tunnel.py", run_name="__main__")
        except SystemExit:
            pass


@patch("usbip_gui.ssl_tunnel.sys")
@patch.dict("os.environ", {"APPDATA": "/mock/appdata"})
@patch("usbip_gui.ssl_tunnel.os.makedirs")
def test_get_cert_paths_windows(
    _mock_makedirs: MagicMock, mock_sys: MagicMock
):
    """Test get_cert_paths on Windows with APPDATA env var."""
    mock_sys.platform = "win32"
    cert, key = get_cert_paths()
    assert cert == os.path.join("/mock/appdata/usbip-gui", "server.crt")
    assert key == os.path.join("/mock/appdata/usbip-gui", "server.key")


@patch("usbip_gui.ssl_tunnel.sys")
@patch("usbip_gui.ssl_tunnel.os.path.expanduser")
@patch.dict("os.environ", {}, clear=True)
@patch("usbip_gui.ssl_tunnel.os.makedirs")
def test_get_cert_paths_windows_no_appdata(
    _mock_makedirs: MagicMock, mock_expanduser: MagicMock, mock_sys: MagicMock
):
    """Test get_cert_paths on Windows without APPDATA env var."""
    mock_sys.platform = "win32"
    mock_expanduser.return_value = "/mock/home"
    cert, key = get_cert_paths()
    assert cert == os.path.join(
        "/mock/home", "AppData", "Roaming", "usbip-gui", "server.crt"
    )
    assert key == os.path.join(
        "/mock/home", "AppData", "Roaming", "usbip-gui", "server.key"
    )
