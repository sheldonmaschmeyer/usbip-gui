"""Client tab implementation for managing remote USB device connections."""

from tkinter import BooleanVar, Widget, Event
from tkinter.ttk import (
    Frame,
    Label,
    Entry,
    Button,
    Scrollbar,
    Treeview,
    Checkbutton,
)
from tkinter import messagebox
import json
import socket
import ssl
import hashlib
import subprocess
import threading
import os
import sys
import re
import random
import time
from typing import List, Tuple
from urllib.parse import urlparse

from .common import (
    get_translator,
    USBIPD_PORT,
    tunnel_state,
    ToolTip,
    get_config_dir,
)

t = get_translator("client")

DEVICE_COLUMNS = [t("Bus ID"), t("Manufacturer"), t("Description")]
ATTACHED_COLUMNS = [
    t("Host"),
    t("Port"),
    t("Bus ID"),
    t("Manufacturer"),
    t("Description"),
]


def parse_remote_list(text: str) -> List[Tuple[str, str, str]]:
    """Parse remote list."""
    if "no exportable devices found on" in text:
        return []

    rows: List[Tuple[str, str, str]] = []
    busid_regex = re.compile("^\\d+-\\d+$|^\\d+-\\d+\\.\\d+$")
    lines = text.strip().split("\n")
    for line in lines:
        vals = line.strip().split(":")
        if len(vals) < 4:
            continue
        m = busid_regex.match(vals[0].strip())
        if m:
            rows.append(
                (
                    vals[0].strip(),
                    vals[1].strip(),
                    vals[2].strip() + ":" + vals[3].strip(),
                )
            )
    return rows


def parse_attached_list(text: str) -> List[Tuple[str, int, str, str, str]]:
    """Parse attached list."""
    rows: List[Tuple[str, int, str, str, str]] = []
    lines = text.strip().split("\n")
    for i, line in enumerate(lines):
        if "Port " in line:
            port = int(line.strip().split(":")[0].replace("Port ", ""))
            info_line = lines[i + 1]
            busid_line = lines[i + 2]

            info = info_line.strip().split(":")
            manufacturer = info[0].strip()
            description = info[1].strip() + ":" + info[2].strip()

            businfo = busid_line.strip().split("->")
            bus_id = businfo[0].strip()
            host = urlparse(businfo[1].strip())[1]  # netloc

            rows.append((host, port, bus_id, manufacturer, description))
    return rows


def get_or_create_client_tunnel(
    host: str, port: int, secure: bool, password: str
) -> Tuple[str, int]:
    """Get or create client tunnel."""
    if not secure:
        return host, port

    context = ssl.create_default_context()
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    try:
        with socket.create_connection((host, port)) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                cert_der = ssock.getpeercert(binary_form=True)

        if not cert_der:
            raise ValueError("No certificate provided by server")

        fingerprint = hashlib.sha256(cert_der).hexdigest().upper()
        it = iter(fingerprint)
        fingerprint = ":".join(a + b for a, b in zip(it, it))

        known_hosts_path = get_config_dir() / "known_hosts.json"
        known_hosts = {}
        if os.path.exists(known_hosts_path):
            with open(known_hosts_path, "r", encoding="utf-8") as f:
                known_hosts = json.load(f)

        host_key = f"{host}:{port}"
        if host_key not in known_hosts or known_hosts[host_key] != fingerprint:
            msg = t("cert_fingerprint_msg").format(fingerprint)
            if messagebox.askyesno(t("Certificate Check"), msg):
                known_hosts[host_key] = fingerprint
                os.makedirs(os.path.dirname(known_hosts_path), exist_ok=True)
                with open(known_hosts_path, "w", encoding="utf-8") as f:
                    json.dump(known_hosts, f)
            else:
                return "", 0

        if not password:
            messagebox.showerror(
                t("Error"), t("Password required for secure connection")
            )
            return "", 0

        with socket.create_connection((host, port)) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                test_cert_der = ssock.getpeercert(binary_form=True)
                if test_cert_der:
                    test_fp = hashlib.sha256(test_cert_der).hexdigest().upper()
                    it = iter(test_fp)
                    test_fp = ":".join(a + b for a, b in zip(it, it))
                    if test_fp != fingerprint:
                        raise ValueError(
                            "Fingerprint mismatch during auth check"
                        )

                pwd_bytes = password.encode("utf-8")
                pwd_len = len(pwd_bytes)
                ssock.sendall(pwd_len.to_bytes(4, byteorder="big") + pwd_bytes)

                response = ssock.recv(1)
                if response != b"\x01":
                    messagebox.showerror(t("Error"), t("auth_failed_msg"))
                    return "", 0

    except (OSError, ValueError) as e:
        messagebox.showerror(
            t("Error"), t(f"Failed to check certificate: {e}")
        )
        return "", 0

    key = (host, port)
    if key in tunnel_state.client_processes:
        local_port, proc, cached_password = tunnel_state.client_processes[key]
        if proc.poll() is None:
            if cached_password == password:
                return "127.0.0.1", local_port
            tunnel_state.client_processes.pop(key)
            proc.kill()

    local_port = random.randint(40000, 50000)

    def run_tunnel():
        with subprocess.Popen(
            [
                sys.executable,
                os.path.join(
                    os.path.dirname(os.path.dirname(__file__)), "ssl_tunnel.py"
                ),
                "client",
                "--listen-port",
                str(local_port),
                "--remote-host",
                host,
                "--remote-port",
                str(port),
                "--password",
                password,
                "--fingerprint",
                fingerprint,
            ]
        ) as proc:
            tunnel_state.client_processes[key] = (local_port, proc, password)
            proc.wait()

    threading.Thread(target=run_tunnel, daemon=True).start()

    time.sleep(1)
    return "127.0.0.1", local_port


def list_remote_usb(
    server_ip: str, port: int = 3240, secure: bool = False, password: str = ""
) -> List[Tuple[str, str, str]]:
    """List remote usb."""
    target_ip, target_port = get_or_create_client_tunnel(
        server_ip, port, secure, password
    )
    if not target_ip:
        return []
    result = subprocess.run(
        [
            "sudo",
            "usbip",
            "--tcp-port",
            str(target_port),
            "list",
            "--remote=" + target_ip,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return parse_remote_list(result.stdout)


def list_attached_usb() -> List[Tuple[str, int, str, str, str]]:
    """List attached usb."""
    result = subprocess.run(
        ["sudo", "usbip", "port"], capture_output=True, text=True, check=False
    )
    return parse_attached_list(result.stdout)


def attach_remote_usb(
    server_ip: str,
    bus_id: str,
    port: int = 3240,
    secure: bool = False,
    password: str = "",
):
    """Attach remote usb."""
    target_ip, target_port = get_or_create_client_tunnel(
        server_ip, port, secure, password
    )
    if not target_ip:
        return subprocess.CompletedProcess(
            args=[], returncode=-1, stdout="", stderr=""
        )
    result = subprocess.run(
        [
            "sudo",
            "usbip",
            "--tcp-port",
            str(target_port),
            "attach",
            "--remote=" + target_ip,
            "--busid=" + bus_id,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return result


def detach_remote_usb(port: int):
    """Detach remote usb."""
    subprocess.run(
        ["sudo", "usbip", "detach", "--port=" + str(port)],
        capture_output=True,
        text=True,
        check=False,
    )


class ClientTab:
    """Clienttab."""

    def __init__(self, parent: Widget):
        """Initialize the class instance."""
        self.frame = Frame(parent)

        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)
        self.frame.rowconfigure(3, weight=1)

        self.remote_control_frame = Frame(self.frame)
        self.remote_list_label = Label(
            self.remote_control_frame, text=t("Remote USB Devices for ")
        )
        self.remote_ip_input = Entry(self.remote_control_frame, width=15)
        self.remote_ip_input.insert(0, "127.0.0.1")
        self.remote_port_input = Entry(self.remote_control_frame, width=6)
        self.remote_port_input.insert(0, str(USBIPD_PORT))
        self.remote_secure_var = BooleanVar(value=True)
        self.remote_secure_checkbox = Checkbutton(
            self.remote_control_frame,
            text=t("Secure"),
            variable=self.remote_secure_var,
            command=lambda: self.check_secure_warning(self.remote_secure_var),
        )
        self.remote_password_input = Entry(
            self.remote_control_frame, width=15, show="*"
        )

        self.remote_list_refresh_button = Button(
            self.remote_control_frame,
            text=t("Refresh"),
            command=self.refresh_remote,
        )
        ToolTip(self.remote_list_refresh_button, t("remote_refresh_tooltip"))
        self.remote_list_attach_button = Button(
            self.remote_control_frame,
            text=t("Attach Device"),
            command=self.attach_remote,
        )
        ToolTip(self.remote_list_attach_button, t("remote_attach_tooltip"))

        self.remote_list_frame = Frame(self.frame)
        self.remote_scroll = Scrollbar(
            self.remote_list_frame, orient="vertical"
        )
        self.remote_listbox = Treeview(
            self.remote_list_frame,
            columns=DEVICE_COLUMNS,
            show="headings",
            yscrollcommand=self.remote_scroll.set,
        )
        self.remote_scroll.config(
            command=getattr(self.remote_listbox, "yview")
        )
        self.remote_scroll.pack(side="right", fill="y")
        self.remote_listbox.pack(side="left", fill="both", expand=True)

        for col in DEVICE_COLUMNS:
            self.remote_listbox.heading(col, text=col)

        self.remote_listbox.bind("<Double-1>", self.on_double_click_remote)

        remote_devices = list_remote_usb("127.0.0.1", USBIPD_PORT)
        for device in remote_devices:
            self.remote_listbox.insert("", "end", values=device)

        self.remote_list_label.grid(column=0, row=0, padx=10)
        self.remote_ip_input.grid(column=1, row=0, padx=10)
        self.remote_port_input.grid(column=2, row=0, padx=10)
        self.remote_secure_checkbox.grid(column=3, row=0, padx=5)
        self.remote_password_input.grid(column=4, row=0, padx=5)
        self.remote_list_refresh_button.grid(column=5, row=0, padx=10)
        self.remote_list_attach_button.grid(column=6, row=0, padx=10)

        self.remote_control_frame.grid(
            column=0, row=0, sticky="ew", pady=(10, 0)
        )
        self.remote_list_frame.grid(
            column=0, row=1, sticky="nsew", padx=10, pady=10
        )

        # Attached devices
        self.attached_control_frame = Frame(self.frame)
        self.attached_list_label = Label(
            self.attached_control_frame, text=t("Attached Devices")
        )
        self.attached_list_refresh_button = Button(
            self.attached_control_frame,
            text=t("Refresh"),
            command=self.refresh_attached,
        )
        ToolTip(
            self.attached_list_refresh_button, t("attached_refresh_tooltip")
        )
        self.detach_button = Button(
            self.attached_control_frame,
            text=t("Detach Device"),
            command=self.detach_remote,
        )
        ToolTip(self.detach_button, t("attached_detach_tooltip"))

        self.attached_list_frame = Frame(self.frame)
        self.attached_scroll = Scrollbar(
            self.attached_list_frame, orient="vertical"
        )
        self.attached_listbox = Treeview(
            self.attached_list_frame,
            columns=ATTACHED_COLUMNS,
            show="headings",
            yscrollcommand=self.attached_scroll.set,
        )
        self.attached_scroll.config(
            command=getattr(self.attached_listbox, "yview")
        )
        self.attached_scroll.pack(side="right", fill="y")
        self.attached_listbox.pack(side="left", fill="both", expand=True)

        for col in ATTACHED_COLUMNS:
            self.attached_listbox.heading(col, text=col)

        self.attached_listbox.bind("<Double-1>", self.on_double_click_attached)

        attached_devices = list_attached_usb()
        for attached_device in attached_devices:
            self.attached_listbox.insert("", "end", values=attached_device)

        self.attached_list_label.grid(column=0, row=0, padx=10)
        self.attached_list_refresh_button.grid(column=1, row=0, padx=10)
        self.detach_button.grid(column=2, row=0, padx=10)

        self.attached_control_frame.grid(
            column=0, row=2, sticky="ew", pady=(10, 0)
        )
        self.attached_list_frame.grid(
            column=0, row=3, sticky="nsew", padx=10, pady=10
        )

    def check_secure_warning(self, var: BooleanVar):
        """Check secure warning."""
        if not var.get():
            messagebox.showwarning(t("Warning"), t("insecure_warning_msg"))

    def refresh_remote(self):
        """Refresh remote."""
        server_ip = self.remote_ip_input.get()
        try:
            port = int(self.remote_port_input.get())
        except ValueError:
            messagebox.showerror(t("Error"), t("Invalid port number"))
            return
        secure = self.remote_secure_var.get()
        password = self.remote_password_input.get()

        remote_devices = list_remote_usb(server_ip, port, secure, password)
        self.remote_listbox.delete(*self.remote_listbox.get_children())
        for device in remote_devices:
            self.remote_listbox.insert("", "end", values=device)

    def refresh_attached(self):
        """Refresh attached."""
        attached_devices = list_attached_usb()
        self.attached_listbox.delete(*self.attached_listbox.get_children())
        for attached_device in attached_devices:
            self.attached_listbox.insert("", "end", values=attached_device)

    def attach_remote(self):
        """Attach remote."""
        server_ip = self.remote_ip_input.get()
        try:
            port = int(self.remote_port_input.get())
        except ValueError:
            messagebox.showerror(t("Error"), t("Invalid port number"))
            return
        selection = self.remote_listbox.selection()
        if not selection:
            messagebox.showerror(t("Error"), t("no selection to attach"))
            return

        secure = self.remote_secure_var.get()
        password = self.remote_password_input.get()
        bus_id = self.remote_listbox.item(selection[0])["values"][0]

        attach_remote_usb(server_ip, str(bus_id), port, secure, password)
        time.sleep(0.5)
        self.refresh_remote()
        self.refresh_attached()

    def detach_remote(self):
        """Detach remote."""
        selection = self.attached_listbox.selection()
        if not selection:
            messagebox.showerror(t("Error"), t("no selection to detach"))
            return
        port = int(self.attached_listbox.item(selection[0])["values"][1])
        detach_remote_usb(port)
        time.sleep(0.5)
        self.refresh_remote()
        self.refresh_attached()

    def on_double_click_remote(self, _event: Event) -> None:
        """Attach remote usb on double click."""
        if self.remote_listbox.selection():
            self.attach_remote()

    def on_double_click_attached(self, _event: Event) -> None:
        """Detach remote usb on double click."""
        if self.attached_listbox.selection():
            self.detach_remote()
