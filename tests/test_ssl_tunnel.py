"""Tests for the ssl_tunnel module."""

import os
import runpy
import sys
from unittest.mock import MagicMock, patch

from usbip_gui.ssl_tunnel import (
    find_openssl,
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
import usbip_gui.ssl_tunnel as ssl_tunnel_mod


def test_get_cert_fingerprint_missing_file():
    """Test getting fingerprint of a missing file returns a fallback."""
    fingerprint = get_cert_fingerprint("/non/existent/path/to/cert.pem")
    assert fingerprint == "No certificate"


def test_is_transient_windows_tls_abort_true():
    """Test transient Windows TLS abort classifier true cases."""
    is_transient = getattr(ssl_tunnel_mod, "_is_transient_windows_tls_abort")
    err = OSError("boom")
    err.winerror = 10053  # type: ignore[attr-defined]
    assert is_transient(err)

    err2 = OSError("boom")
    err2.winerror = 10054  # type: ignore[attr-defined]
    assert is_transient(err2)


def test_is_transient_windows_tls_abort_false():
    """Test transient Windows TLS abort classifier false case."""
    is_transient = getattr(ssl_tunnel_mod, "_is_transient_windows_tls_abort")
    err = OSError("boom")
    err.winerror = 10060  # type: ignore[attr-defined]
    assert not is_transient(err)


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
    mock_run.return_value.returncode = 0
    generate_self_signed_cert("/path/to/cert", "/path/to/key")
    mock_run.assert_called_once()


@patch("usbip_gui.ssl_tunnel.find_openssl", return_value="/usr/bin/openssl")
@patch("usbip_gui.ssl_tunnel.subprocess.run")
def test_generate_self_signed_cert_failure(
    mock_run: MagicMock, _mock_find: MagicMock
):
    """Test generate_self_signed_cert raises OSError with openssl's output."""
    mock_run.return_value.returncode = 1
    mock_run.return_value.stderr = "unable to load config info\n"
    mock_run.return_value.stdout = ""
    try:
        generate_self_signed_cert("/path/to/cert", "/path/to/key")
        assert False, "Expected OSError"
    except OSError as e:
        assert "unable to load config info" in str(e)


@patch("usbip_gui.ssl_tunnel.find_openssl", return_value="/usr/bin/openssl")
@patch("usbip_gui.ssl_tunnel.subprocess.run")
def test_generate_self_signed_cert_uses_own_config(
    mock_run: MagicMock, _mock_find: MagicMock
):
    """Test generate_self_signed_cert supplies its own minimal -config file."""
    mock_run.return_value.returncode = 0
    generate_self_signed_cert("/path/to/cert", "/path/to/key")
    args = mock_run.call_args.args[0]
    assert "-config" in args
    config_path = args[args.index("-config") + 1]
    # The temp config file is cleaned up after the call.
    assert not os.path.exists(config_path)


@patch("usbip_gui.ssl_tunnel.os.remove", side_effect=OSError)
@patch("usbip_gui.ssl_tunnel.find_openssl", return_value="/usr/bin/openssl")
@patch("usbip_gui.ssl_tunnel.subprocess.run")
def test_generate_self_signed_cert_cleanup_oserror(
    mock_run: MagicMock, _mock_find: MagicMock, _mock_remove: MagicMock
):
    """Test generate_self_signed_cert tolerates a failed temp-file cleanup."""
    mock_run.return_value.returncode = 0
    generate_self_signed_cert("/path/to/cert", "/path/to/key")
    mock_run.assert_called_once()


@patch("usbip_gui.ssl_tunnel.os.path.exists", return_value=True)
@patch("usbip_gui.ssl_tunnel.sys")
def test_find_openssl_linux(mock_sys: MagicMock, _mock_exists: MagicMock):
    """Test find_openssl resolves the pixi/conda env executable on Linux."""
    mock_sys.platform = "linux"
    mock_sys.prefix = "/opt/pixi/envs/default"
    result = find_openssl()
    assert result == os.path.join("/opt/pixi/envs/default", "bin", "openssl")


@patch("usbip_gui.ssl_tunnel.os.path.exists", return_value=True)
@patch("usbip_gui.ssl_tunnel.sys")
def test_find_openssl_windows(mock_sys: MagicMock, _mock_exists: MagicMock):
    """Test find_openssl resolves the pixi/conda env executable on Windows."""
    mock_sys.platform = "win32"
    mock_sys.prefix = r"C:\pixi\envs\default"
    result = find_openssl()
    assert result == os.path.join(
        r"C:\pixi\envs\default", "Library", "bin", "openssl.exe"
    )


@patch("usbip_gui.ssl_tunnel.os.path.exists", return_value=False)
@patch("usbip_gui.ssl_tunnel.sys")
def test_find_openssl_not_found(mock_sys: MagicMock, _mock_exists: MagicMock):
    """Test find_openssl raises a helpful error when missing from the env."""
    mock_sys.platform = "linux"
    mock_sys.prefix = "/opt/pixi/envs/default"
    try:
        find_openssl()
        assert False, "Expected FileNotFoundError"
    except FileNotFoundError as e:
        assert "pixi install" in str(e)


def test_recv_exact():
    """Test recv_exact function."""
    mock_sock = MagicMock()
    mock_sock.recv.side_effect = [b"he", b"ll", b"o"]
    data = recv_exact(mock_sock, 5)
    assert data == b"hello"


@patch.dict("os.environ", {}, clear=True)
@patch("usbip_gui.ssl_tunnel.os.path.expanduser")
@patch("usbip_gui.ssl_tunnel.os.makedirs")
@patch("usbip_gui.ssl_tunnel.sys")
def test_get_cert_paths(
    mock_sys: MagicMock,
    mock_makedirs: MagicMock,
    mock_expanduser: MagicMock,
):
    """Test getting config paths."""
    mock_sys.platform = "linux"
    mock_expanduser.return_value = "/mock/dir"
    cert, key = get_cert_paths()
    made_path = mock_makedirs.call_args.args[0]
    assert os.path.normpath(made_path) == os.path.normpath(
        "/mock/dir/usbip-gui"
    )
    assert mock_makedirs.call_args.kwargs == {"exist_ok": True}
    assert os.path.normpath(cert) == os.path.normpath(
        "/mock/dir/usbip-gui/server.crt"
    )
    assert os.path.normpath(key) == os.path.normpath(
        "/mock/dir/usbip-gui/server.key"
    )


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


@patch("usbip_gui.ssl_tunnel.socket.socket")
def test_client_handle_connection_close_raises_oserror(
    _mock_socket: MagicMock,
):
    """Test client close OSError is tolerated in cleanup."""
    local_sock = MagicMock()
    context = MagicMock()
    ssl_sock = context.wrap_socket.return_value
    ssl_sock.recv.return_value = b"\x00"
    ssl_sock.close.side_effect = OSError("close failed")

    client_handle_connection(local_sock, ("127.0.0.1", 1234), "pass", context)

    ssl_sock.connect.assert_called_once_with(("127.0.0.1", 1234))
    ssl_sock.close.assert_called_once()


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


@patch("usbip_gui.ssl_tunnel.time.sleep")
@patch("usbip_gui.ssl_tunnel.socket.socket")
@patch("usbip_gui.ssl_tunnel.forward")
def test_client_handle_connection_retries_winerror_10053(
    mock_forward: MagicMock,
    mock_socket_ctor: MagicMock,
    _mock_sleep: MagicMock,
):
    """Test transient WinError 10053 is retried and then succeeds."""
    local_sock = MagicMock()
    context = MagicMock()

    first_ssl_sock = MagicMock()
    second_ssl_sock = MagicMock()

    transient = ConnectionAbortedError("aborted")
    transient.winerror = 10053  # type: ignore[attr-defined]
    first_ssl_sock.connect.side_effect = transient
    second_ssl_sock.recv.return_value = b"\x01"

    context.wrap_socket.side_effect = [first_ssl_sock, second_ssl_sock]

    client_handle_connection(local_sock, ("127.0.0.1", 1234), "pass", context)

    assert context.wrap_socket.call_count == 2
    mock_forward.assert_called_once_with(local_sock, second_ssl_sock)
    mock_socket_ctor.assert_called()


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
    expected_cert = os.path.normpath("/mock/appdata/usbip-gui/server.crt")
    expected_key = os.path.normpath("/mock/appdata/usbip-gui/server.key")
    assert os.path.normpath(cert) == expected_cert
    assert os.path.normpath(key) == expected_key


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
