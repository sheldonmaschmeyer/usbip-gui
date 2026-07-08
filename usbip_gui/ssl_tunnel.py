"""Module for SSL tunneling."""

import ssl
import socket
import threading
import argparse
import os
import subprocess
import hashlib


def get_cert_paths() -> tuple[str, str]:
    """
    Get the default paths for the SSL certificate and private key.

    Returns:
        tuple[str, str]: A tuple containing the certificate path and key path.
    """
    config_dir = os.path.expanduser("~/.config/usbip-gui")
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, "server.crt"), os.path.join(
        config_dir, "server.key"
    )


def get_cert_fingerprint(cert_path: str) -> str:
    """
    Calculate and return the SHA-256 fingerprint of the given certificate.

    Args:
        cert_path (str): Path to the PEM encoded certificate file.

    Returns:
        str: The formatted SHA-256 fingerprint, or "No certificate" if missing.
    """
    if not os.path.exists(cert_path):
        return "No certificate"
    with open(cert_path, "r", encoding="utf-8") as f:
        cert_pem = f.read()
    cert_der = ssl.PEM_cert_to_DER_cert(cert_pem)
    fingerprint = hashlib.sha256(cert_der).hexdigest().upper()
    it = iter(fingerprint)
    return ":".join(a + b for a, b in zip(it, it))


def generate_self_signed_cert(cert_path: str, key_path: str) -> None:
    """
    Generate a self-signed X.509 certificate and private key using OpenSSL.

    Args:
        cert_path (str): The file path where the generated certificate will
            be saved.
        key_path (str): The file path where the generated private key will
            be saved.
    """
    subprocess.run(
        [
            "/usr/bin/openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:4096",
            "-nodes",
            "-out",
            cert_path,
            "-keyout",
            key_path,
            "-days",
            "365",
            "-subj",
            "/CN=usbip-gui-secure",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def recv_exact(sock: socket.socket, n: int) -> bytes:
    """Receive exactly n bytes from a socket."""
    data = bytearray()
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return bytes()
        data.extend(packet)
    return bytes(data)


def server_handle_connection(
    client_socket: socket.socket,
    target_host: str,
    target_port: int,
    password: str,
) -> None:
    """
    Handle an incoming client connection on the server side.

    Authenticates the client using a pre-shared password. If authentication
    is successful, it connects to the target host and port (typically the
    local usbip daemon) and forwards traffic between the client and the target.

    Args:
        client_socket (socket.socket): The accepted SSL client connection.
        target_host (str): The host to forward authenticated traffic to.
        target_port (int): The port to forward authenticated traffic to.
        password (str): The pre-shared password required for authentication.
    """
    try:
        pwd_bytes = password.encode("utf-8")

        length_data = recv_exact(client_socket, 4)
        if not length_data or len(length_data) < 4:
            return
        cli_len = int.from_bytes(length_data, byteorder="big")
        cli_pwd = recv_exact(client_socket, cli_len)
        if cli_pwd != pwd_bytes:
            print("Authentication failed")
            try:
                client_socket.sendall(b"\x00")
            except OSError:
                pass
            return

        client_socket.sendall(b"\x01")

        target_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        target_socket.connect((target_host, target_port))

        forward(client_socket, target_socket)
    except OSError as e:
        print(f"Server connection error: {e}")
    finally:
        try:
            client_socket.close()
        except OSError:
            pass


def client_handle_connection(
    local_socket: socket.socket,
    remote_addr: tuple[str, int],
    password: str,
    context: ssl.SSLContext,
    expected_fingerprint: str = "",
) -> None:
    """
    Handle a local client connection and tunnel it to the remote server.

    Connects to the remote server via SSL, sends the pre-shared password for
    authentication, and then forwards traffic between the local connection and
    the remote server.

    Args:
        local_socket (socket.socket): The accepted local unencrypted
            connection.
        remote_addr (tuple[str, int]): Tuple containing remote host and port.
        password (str): The pre-shared password for authentication.
        context (ssl.SSLContext): The SSL context to wrap the remote socket
            with.
    """
    remote_host, remote_port = remote_addr
    try:
        remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ssl_remote_socket = context.wrap_socket(
            remote_socket, server_hostname=remote_host
        )
        ssl_remote_socket.connect((remote_host, remote_port))

        if expected_fingerprint:
            cert_der = ssl_remote_socket.getpeercert(binary_form=True)
            if not cert_der:
                print(
                    "Client connection error: "
                    "No certificate provided by server"
                )
                return

            actual_fp = hashlib.sha256(cert_der).hexdigest().upper()
            it = iter(actual_fp)
            actual_fp = ":".join(a + b for a, b in zip(it, it))
            if actual_fp != expected_fingerprint:
                print(
                    "Client connection error: Fingerprint mismatch! "
                    f"Expected {expected_fingerprint}, got {actual_fp}"
                )
                return

        pwd_bytes = password.encode("utf-8")
        pwd_len = len(pwd_bytes)
        ssl_remote_socket.sendall(
            pwd_len.to_bytes(4, byteorder="big") + pwd_bytes
        )

        auth_resp = ssl_remote_socket.recv(1)
        if auth_resp != b"\x01":
            print(
                "Client connection error: "
                "Authentication failed at remote server"
            )
            return

        forward(local_socket, ssl_remote_socket)
    except OSError as e:
        print(f"Client connection error: {e}")
    finally:
        try:
            local_socket.close()
        except OSError:
            pass


def forward(sock1: socket.socket, sock2: socket.socket) -> None:
    """
    Bidirectionally forward traffic between two sockets.

    Args:
        sock1 (socket.socket): The first socket.
        sock2 (socket.socket): The second socket.
    """

    def pump(src: socket.socket, dst: socket.socket) -> None:
        try:
            while True:
                data = src.recv(4096)
                if not data:
                    break
                dst.sendall(data)
        except OSError:
            pass
        finally:
            try:
                src.shutdown(socket.SHUT_RD)
            except OSError:
                pass
            try:
                dst.shutdown(socket.SHUT_WR)
            except OSError:
                pass

    t1 = threading.Thread(target=pump, args=(sock1, sock2))
    t2 = threading.Thread(target=pump, args=(sock2, sock1))
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    sock1.close()
    sock2.close()


def start_server(
    listen_port: int,
    target_port: int,
    password: str,
    bind_host: str = "127.0.0.1",
) -> None:
    """
    Start the SSL proxy server.

    Generates a temporary self-signed certificate, binds to the specified
    listen port on all interfaces, and handles incoming SSL connections.

    Args:
        listen_port (int): The port to listen for incoming SSL connections.
        target_port (int): The local target port to forward authenticated
            traffic to.
        password (str): The password required from clients for authentication.
        bind_host (str): The host interface to bind to (default: 127.0.0.1).
    """
    cert_path, key_path = get_cert_paths()

    try:
        if not os.path.exists(cert_path) or not os.path.exists(key_path):
            generate_self_signed_cert(cert_path, key_path)

        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(certfile=cert_path, keyfile=key_path)

        bindsocket = socket.socket()
        bindsocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        bindsocket.bind((bind_host, listen_port))
        bindsocket.listen(5)

        print(
            f"SSL Server listening on {bind_host}:{listen_port}, "
            f"forwarding to {target_port}"
        )

        while True:
            newsocket, _fromaddr = bindsocket.accept()
            try:
                conn = context.wrap_socket(newsocket, server_side=True)
                threading.Thread(
                    target=server_handle_connection,
                    args=(conn, "127.0.0.1", target_port, password),
                ).start()
            except OSError as e:
                print(f"SSL handshake error: {e}")
    except (OSError, subprocess.CalledProcessError) as e:
        print(f"Server error: {e}")


def start_client(
    listen_port: int,
    remote_host: str,
    remote_port: int,
    password: str,
    fingerprint: str = "",
) -> None:
    """
    Start the SSL proxy client.

    Listens on a local port (loopback interface) for incoming unencrypted
    connections, and forwards them over SSL to the remote server.

    Args:
        listen_port (int): The local port to listen on for unencrypted
            connections.
        remote_host (str): The remote SSL server host to connect to.
        remote_port (int): The remote SSL server port to connect to.
        password (str): The password to authenticate with the remote server.
    """
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    bindsocket = socket.socket()
    bindsocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    bindsocket.bind(("127.0.0.1", listen_port))
    bindsocket.listen(5)

    print(
        f"SSL Client listening on {listen_port}, "
        f"forwarding to {remote_host}:{remote_port}"
    )

    while True:
        newsocket, _fromaddr = bindsocket.accept()
        threading.Thread(
            target=client_handle_connection,
            args=(
                newsocket,
                (remote_host, remote_port),
                password,
                context,
                fingerprint,
            ),
        ).start()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["server", "client"])
    parser.add_argument("--listen-port", type=int, required=True)
    parser.add_argument(
        "--target-port", type=int, required=False
    )  # for server
    parser.add_argument(
        "--remote-host", type=str, required=False
    )  # for client
    parser.add_argument(
        "--remote-port", type=int, required=False
    )  # for client
    parser.add_argument(
        "--fingerprint", type=str, required=False, default=""
    )  # for client
    parser.add_argument(
        "--bind-host", type=str, required=False, default="127.0.0.1"
    )  # for server
    parser.add_argument("--password", type=str, required=True)

    args = parser.parse_args()

    if args.mode == "server":
        start_server(
            args.listen_port, args.target_port, args.password, args.bind_host
        )
    else:
        start_client(
            args.listen_port,
            args.remote_host,
            args.remote_port,
            args.password,
            args.fingerprint,
        )
