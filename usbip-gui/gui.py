"""
A graphical user interface for managing and interacting with USB/IP devices.
"""

# requires python 3.8+
import tkinter as tk
from tkinter import Tk, BooleanVar
from tkinter.ttk import (
    Treeview,
    Frame,
    Label,
    Entry,
    Button,
    Scrollbar,
    Style,
    Checkbutton,
)
import tkinter.messagebox as messagebox
import tkinter.font as tkfont
import subprocess
import re
import time
import os
import sys
import atexit
import random
from typing import List, Tuple, Optional, Dict
from urllib.parse import urlparse
from gettext import textdomain, bindtextdomain, gettext as _
from pathlib import Path

APP_DOMAIN = "usbip-gui"

textdomain(APP_DOMAIN)
_local_localedir = Path(__file__).parent.parent / "share" / "locale"
if _local_localedir.exists():
    bindtextdomain(APP_DOMAIN, localedir=str(_local_localedir))
else:
    bindtextdomain(APP_DOMAIN, localedir="/usr/local/share/locale/")

DEVICE_COLUMNS = [_("Bus ID"), _("Manufacturer"), _("Description")]
DEVICE_COLUMN_WIDTHS = [8, 20, 50]
LOCAL_DEVICE_COLUMNS = [
    _("Bus ID"),
    _("State"),
    _("Manufacturer"),
    _("Description"),
]
ATTACHED_COLUMNS = [
    _("Host"),
    _("Port"),
    _("Bus ID"),
    _("Manufacturer"),
    _("Description"),
]
ATTACHED_COLUMN_WIDTHS = [21, 3, 8, 20, 50]
USBIPD_PORT = 3240
DEFAULT_GEOMETRY = "1300x842"

ssl_server_process: Optional[subprocess.Popen[bytes]] = None
ssl_client_processes: Dict[
    Tuple[str, int], Tuple[int, subprocess.Popen[bytes], str]
] = {}


def cleanup_tunnels():
    """Terminate any background SSL tunnel processes."""
    if ssl_server_process:
        try:
            ssl_server_process.terminate()
        except OSError:
            pass
    for _local_port, proc in ssl_client_processes.values():
        try:
            proc.terminate()
        except OSError:
            pass


atexit.register(cleanup_tunnels)


def init_kernel_modules():
    """Load the required kernel modules for USB/IP."""
    subprocess.run(["sudo", "modprobe", "usbip_host"], check=False)
    subprocess.run(["sudo", "modprobe", "usbip_core"], check=False)
    subprocess.run(["sudo", "modprobe", "vhci_hcd"], check=False)


def init_usbip_server(
    port: int = 3240, secure: bool = False, password: str = ""
):
    """Initialize and start the usbipd server daemon."""
    global ssl_server_process
    subprocess.run(["sudo", "pkill", "usbipd"], check=False)
    if ssl_server_process:
        try:
            ssl_server_process.terminate()
            ssl_server_process.wait()
        except OSError:
            pass
        ssl_server_process = None

    if secure:
        target_port = port + 10000
        subprocess.run(
            ["sudo", "usbipd", "-D", "--tcp-port", str(target_port)],
            check=False,
        )
        ssl_server_process = subprocess.Popen(
            [
                sys.executable,
                os.path.join(os.path.dirname(__file__), "ssl_tunnel.py"),
                "server",
                "--listen-port",
                str(port),
                "--target-port",
                str(target_port),
                "--password",
                password,
            ]
        )
    else:
        subprocess.run(
            ["sudo", "usbipd", "-D", "--tcp-port", str(port)], check=False
        )


def scan():
    """Scan for devices (Placeholder function)."""
    # TODO
    return 0


# sample output to parse for parse_local_list(text)
#  - busid 2-3 (1058:25a3)
#    Western Digital Technologies, Inc. : unknown product (1058:25a3)
#
#  - busid 3-3.2 (046d:c52b)
#    Logitech, Inc. : Unifying Receiver (046d:c52b)
#
#  - busid 3-3.3 (046d:c52b)
#    Logitech, Inc. : Unifying Receiver (046d:c52b)
#
#  - busid 3-3.4 (058f:6366)
#    Alcor Micro Corp. : Multi Flash Reader (058f:6366)
#
#  - busid 4-1 (054c:0268)
#    Sony Corp. : Batch Device / PlayStation 3 Controller (054c:0268)


def parse_local_list(text: str) -> List[Tuple[str, str, str, str]]:
    """Parse the text output of 'usbip list --local'."""
    if not text or not text.strip():
        return []

    rows: List[Tuple[str, str, str, str]] = []
    devices = text.strip().split("\n\n")
    for device in devices:
        # print(device)
        lines = device.strip().split("\n")
        if len(lines) < 2:
            continue
        # print(lines)
        bus_info = lines[0].split(" ")
        man_info = lines[1].split(":")

        bus_id = bus_info[2] if len(bus_info) > 2 else ""
        manufacturer = man_info[0] if len(man_info) > 0 else ""
        description = ":".join(man_info[1:]) if len(man_info) > 1 else ""

        state = _("Unbound")
        if bus_id:
            driver_path = f"/sys/bus/usb/devices/{bus_id}/driver"
            if os.path.exists(driver_path) and os.path.islink(driver_path):
                driver = os.path.basename(os.readlink(driver_path))
                if driver == "usbip-host":
                    state = _("Bound")

        rows.append(
            (
                bus_id,
                state,
                manufacturer,
                description,
            )
        )
    # print(rows)
    return rows


# sample output to parse for parse_remote(text)
# Exportable USB devices
# ======================
#  - 192.168.1.103
#       1-1.3: SanDisk Corp. : Cruzer (0781:5530)
#            : /sys/devices/platform/soc/20980000.usb/usb1/1-1/1-1.3
#            : (Defined at Interface level) (00/00/00)
#            :  0 - Mass Storage / SCSI / Bulk-Only (08/06/50)


def parse_remote_list(text: str) -> List[Tuple[str, str, str]]:
    """Parse the text output of 'usbip list --remote'."""
    if "no exportable devices found on" in text:
        return []

    rows: List[Tuple[str, str, str]] = []

    busid_regex = re.compile("^\\d+-\\d+$|^\\d+-\\d+\\.\\d+$")
    lines = text.strip().split("\n")
    for line in lines:
        vals = line.strip().split(":")
        print(vals)
        m = busid_regex.match(vals[0])
        if m:  # the first value is a bus_id, grab the info
            rows.append((vals[0], vals[1], vals[2] + ":" + vals[3]))
    return rows


# sample output to parse for parse_attached_list(text)
# Imported USB devices
# ====================
# Port 00: <Port in Use> at Full Speed(12 Mbps)
#        Sony Corp. : Batch Device / PlayStation 3 Controller (054c:0268)
#        5-1 -> usbip://192.168.1.103:3240/1-1.4
#            -> remote bus/dev 001/005


def parse_attached_list(text: str) -> List[Tuple[str, int, str, str, str]]:
    """Parse the text output of 'usbip port'."""
    rows: List[Tuple[str, int, str, str, str]] = []

    lines = text.strip().split("\n")
    for i, line in enumerate(lines):
        if "Port " in line:
            port = int(line.strip().split(":")[0].replace("Port ", ""))
            info_line = lines[i + 1]
            busid_line = lines[i + 2]

            info = info_line.strip().split(":")
            manufacturer = info[0]
            description = info[1] + ":" + info[2]

            businfo = busid_line.strip().split("->")
            bus_id = businfo[0].strip()
            host = urlparse(businfo[1].strip())[1]  # netloc

            rows.append((host, port, bus_id, manufacturer, description))
    print(rows)
    return rows


def list_local_usb() -> List[Tuple[str, str, str, str]]:
    """Execute usbip to list local devices and return parsed rows."""
    result = subprocess.run(
        ["sudo", "usbip", "list", "--local"],
        capture_output=True,
        text=True,
        check=False,
    )
    return parse_local_list(result.stdout)


def get_or_create_client_tunnel(
    host: str, port: int, secure: bool, password: str
) -> Tuple[str, int]:
    """
    Get an existing local proxy tunnel for a remote host, or create a new one.

    If secure is True, this spawns a local instance of ssl_tunnel.py configured
    to forward traffic securely to the specified remote host and port, caching
    the process to avoid reconnecting.

    Returns:
        tuple: (target_ip, target_port) pointing to the local tunnel if secure,
               otherwise returns the original host and port. Returns ("", 0) on abort.
    """
    if not secure:
        return host, port

    import ssl
    import socket
    import hashlib
    import json

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
            
        fingerprint = hashlib.sha256(cert_der).hexdigest()
        fingerprint = ":".join(fingerprint[i:i+2] for i in range(0, len(fingerprint), 2)).upper()
        
        known_hosts_path = os.path.expanduser("~/.config/usbip-gui/known_hosts.json")
        known_hosts = {}
        if os.path.exists(known_hosts_path):
            with open(known_hosts_path, "r") as f:
                known_hosts = json.load(f)
                
        host_key = f"{host}:{port}"
        if host_key not in known_hosts or known_hosts[host_key] != fingerprint:
            msg = _("The server's certificate fingerprint is:\n\n{}\n\nDo you want to accept this connection?").format(fingerprint)
            if messagebox.askyesno(_("Certificate Check"), msg):
                known_hosts[host_key] = fingerprint
                os.makedirs(os.path.dirname(known_hosts_path), exist_ok=True)
                with open(known_hosts_path, "w") as f:
                    json.dump(known_hosts, f)
            else:
                return "", 0

        if not password:
            messagebox.showerror(_("Error"), _("Password required for secure connection"))
            return "", 0

        # Now that the fingerprint is trusted, verify the password
        with socket.create_connection((host, port)) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                test_cert_der = ssock.getpeercert(binary_form=True)
                if test_cert_der:
                    test_fp = hashlib.sha256(test_cert_der).hexdigest().upper()
                    test_fp = ":".join(test_fp[i:i+2] for i in range(0, len(test_fp), 2))
                    if test_fp != fingerprint:
                        raise ValueError("Fingerprint mismatch during auth check")
                        
                pwd_bytes = password.encode("utf-8")
                pwd_len = len(pwd_bytes)
                ssock.sendall(pwd_len.to_bytes(4, byteorder="big") + pwd_bytes)
                
                response = ssock.recv(1)
                if response != b"\x01":
                    messagebox.showerror(_("Error"), _("Authentication failed. Please check your password."))
                    return "", 0

    except Exception as e:
        messagebox.showerror(_("Error"), _(f"Failed to check certificate: {e}"))
        return "", 0

    key = (host, port)
    if key in ssl_client_processes:
        local_port, proc, cached_password = ssl_client_processes[key]
        if proc.poll() is None:
            if cached_password == password:
                return "127.0.0.1", local_port
            else:
                proc.terminate()
                proc.wait()

    local_port = random.randint(40000, 50000)
    proc = subprocess.Popen(
        [
            sys.executable,
            os.path.join(os.path.dirname(__file__), "ssl_tunnel.py"),
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
    )
    ssl_client_processes[key] = (local_port, proc, password)
    time.sleep(1)  # Give tunnel time to start
    return "127.0.0.1", local_port


def list_remote_usb(
    server_ip: str, port: int = 3240, secure: bool = False, password: str = ""
) -> List[Tuple[str, str, str]]:
    """Execute usbip to list exportable devices on a remote server."""
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


def bind_local_usb(bus_id: str):
    """Execute usbip to bind a local device by bus ID."""
    result = subprocess.run(
        ["sudo", "usbip", "bind", "--busid=" + bus_id],
        capture_output=True,
        text=True,
        check=False,
    )
    print(result.stdout)
    print(result.stderr)
    return result


def unbind_local_usb(bus_id: str):
    """Execute usbip to unbind a local device by bus ID."""
    result = subprocess.run(
        ["sudo", "usbip", "unbind", "--busid=" + bus_id],
        capture_output=True,
        text=True,
        check=False,
    )
    print(result.stdout)
    print(result.stderr)
    return result


def list_attached_usb() -> List[Tuple[str, int, str, str, str]]:
    """Execute usbip to list currently attached remote devices."""
    result = subprocess.run(
        ["sudo", "usbip", "port"], capture_output=True, text=True, check=False
    )
    print(result.stdout)
    print(result.stderr)
    return parse_attached_list(result.stdout)


def attach_remote_usb(
    server_ip: str,
    bus_id: str,
    port: int = 3240,
    secure: bool = False,
    password: str = "",
):
    """Execute usbip to attach a remote device by bus ID."""
    target_ip, target_port = get_or_create_client_tunnel(
        server_ip, port, secure, password
    )
    if not target_ip:
        return subprocess.CompletedProcess(args=[], returncode=-1, stdout="", stderr="")
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
    print(result.stdout)
    print(result.stderr)
    return result


def detach_remote_usb(port: int):
    """Execute usbip to detach an imported device by port."""
    result = subprocess.run(
        ["sudo", "usbip", "detach", "--port=" + str(port)],
        capture_output=True,
        text=True,
        check=False,
    )
    print(result.stdout)
    print(result.stderr)


# def update_list(list, values):


class ToolTip:
    """A simple tooltip widget for Tkinter."""

    def __init__(self, widget: tk.Widget, text: str):
        """Initialize the tooltip with a target widget and text."""
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event: Optional[tk.Event] = None):
        """Display the tooltip on the screen."""
        if self.tooltip_window or not self.text:
            return
        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + 20
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            tw,
            text=self.text,
            justify="left",
            background="#313244",
            foreground="#cdd6f4",
            relief="solid",
            borderwidth=1,
            font=("Ubuntu", 10),
        )
        label.pack(ipadx=5, ipady=3)

    def hide_tooltip(self, event: Optional[tk.Event] = None):
        """Hide and destroy the tooltip window."""
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


class UsbIpGui:
    """Main application class for the USB/IP GUI."""

    def __init__(self, root: Tk):
        """Initialize the main GUI components."""
        self.root = root
        self.root.wm_title(_("USB/IP Peer"))
        self.root.geometry(DEFAULT_GEOMETRY)

        # Configure grid to be responsive
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)
        self.root.rowconfigure(3, weight=1)
        self.root.rowconfigure(5, weight=1)

        # Remote devices
        self.remote_control_frame = Frame(self.root)
        self.remote_list_label = Label(
            self.remote_control_frame,
            text=_("Remote USB Devices for "),
        )
        self.remote_ip_input = Entry(self.remote_control_frame, width=15)
        self.remote_ip_input.insert(0, "127.0.0.1")
        self.remote_port_input = Entry(self.remote_control_frame, width=6)
        self.remote_port_input.insert(0, str(USBIPD_PORT))
        self.remote_secure_var = BooleanVar(value=True)
        self.remote_secure_checkbox = Checkbutton(
            self.remote_control_frame,
            text=_("Secure"),
            variable=self.remote_secure_var,
            command=lambda: self.check_secure_warning(self.remote_secure_var)
        )
        self.remote_password_input = Entry(
            self.remote_control_frame, width=15, show="*"
        )

        self.remote_list_refresh_button = Button(
            self.remote_control_frame,
            text=_("Refresh"),
            command=self.refresh_remote,
        )
        ToolTip(self.remote_list_refresh_button, _("remote_refresh_tooltip"))
        self.remote_list_attach_button = Button(
            self.remote_control_frame,
            text=_("Attach Device"),
            command=self.attach_remote,
        )
        ToolTip(self.remote_list_attach_button, _("remote_attach_tooltip"))

        self.remote_list_frame = Frame(self.root)

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
            column=0, row=2, sticky="ew", pady=(10, 0)
        )
        self.remote_list_frame.grid(
            column=0, row=3, sticky="nsew", padx=10, pady=10
        )

        # Local devices
        self.local_control_frame = Frame(self.root)
        self.local_list_label = Label(
            self.local_control_frame, text=_("Local USB Devices")
        )
        self.local_port_label = Label(
            self.local_control_frame, text=_("Port ")
        )
        self.local_port_input = Entry(self.local_control_frame, width=6)
        self.local_port_input.insert(0, str(USBIPD_PORT))
        self.local_secure_var = BooleanVar(value=True)
        self.local_secure_checkbox = Checkbutton(
            self.local_control_frame,
            text=_("Secure"),
            variable=self.local_secure_var,
            command=lambda: self.check_secure_warning(self.local_secure_var)
        )
        self.local_password_input = Entry(
            self.local_control_frame, width=15, show="*"
        )

        self.local_server_restart_button = Button(
            self.local_control_frame,
            text=_("Apply Port & Restart"),
            command=self.restart_server,
        )
        ToolTip(self.local_server_restart_button, _("local_restart_tooltip"))
        self.local_port_input.bind("<Return>", lambda e: self.restart_server())
        # Actions Frame
        self.local_actions_frame = Frame(self.local_control_frame)

        self.local_list_refresh_button = Button(
            self.local_actions_frame,
            text=_("Refresh"),
            command=self.refresh_local,
        )
        ToolTip(self.local_list_refresh_button, _("local_refresh_tooltip"))
        self.local_list_bind_button = Button(
            self.local_actions_frame,
            text=_("Bind Device"),
            command=self.bind_local,
        )
        ToolTip(self.local_list_bind_button, _("local_bind_tooltip"))
        self.local_list_unbind_button = Button(
            self.local_actions_frame,
            text=_("Unbind Device"),
            command=self.unbind_local,
        )
        ToolTip(self.local_list_unbind_button, _("local_unbind_tooltip"))

        
        self.local_show_fingerprint_button = Button(
            self.local_control_frame,
            text=_("Show Fingerprint"),
            command=self.show_fingerprint,
        )
        self.local_regen_cert_button = Button(
            self.local_control_frame,
            text=_("Regen Cert"),
            command=self.regenerate_cert,
        )

        self.local_list_frame = Frame(self.root)
        self.local_scroll = Scrollbar(self.local_list_frame, orient="vertical")
        self.local_listbox = Treeview(
            self.local_list_frame,
            columns=LOCAL_DEVICE_COLUMNS,
            show="headings",
            yscrollcommand=self.local_scroll.set,
        )
        self.local_scroll.config(command=getattr(self.local_listbox, "yview"))

        self.local_scroll.pack(side="right", fill="y")
        self.local_listbox.pack(side="left", fill="both", expand=True)

        for col in LOCAL_DEVICE_COLUMNS:
            self.local_listbox.heading(col, text=col)

        local_devices = list_local_usb()
        for device in local_devices:
            self.local_listbox.insert("", "end", values=device)

        self.local_list_label.grid(column=0, row=0, padx=10)
        self.local_port_label.grid(column=1, row=0, padx=(10, 0), sticky="e")
        self.local_port_input.grid(column=2, row=0, padx=(0, 10), sticky="w")
        self.local_secure_checkbox.grid(column=3, row=0, padx=5)
        self.local_password_input.grid(column=4, row=0, padx=5)
        self.local_server_restart_button.grid(column=5, row=0, padx=10)
        self.local_show_fingerprint_button.grid(column=6, row=0, padx=10)
        self.local_regen_cert_button.grid(column=7, row=0, padx=10)

        # Row 1: Actions (placed below Port, left justified)
        self.local_actions_frame.grid(column=1, row=1, columnspan=7, sticky="w", pady=(5, 0))

        self.local_list_refresh_button.grid(column=0, row=0, padx=(10, 5))
        self.local_list_bind_button.grid(column=1, row=0, padx=5)
        self.local_list_unbind_button.grid(column=2, row=0, padx=5)

        self.lang_button = Button(
            self.local_control_frame,
            text="EN / FR",
            command=self.toggle_language,
        )
        ToolTip(self.lang_button, _("lang_toggle_tooltip"))
        self.local_control_frame.columnconfigure(11, weight=1)
        self.lang_button.grid(column=12, row=0, padx=10, sticky="e")

        self.local_control_frame.grid(
            column=0, row=0, sticky="ew", pady=(10, 0)
        )
        self.local_list_frame.grid(
            column=0, row=1, sticky="nsew", padx=10, pady=10
        )

        # Attached devices
        self.attached_control_frame = Frame(self.root)
        self.attached_list_label = Label(
            self.attached_control_frame, text=_("Attached Devices")
        )
        self.attached_list_refresh_button = Button(
            self.attached_control_frame,
            text=_("Refresh"),
            command=self.refresh_attached,
        )
        ToolTip(
            self.attached_list_refresh_button, _("attached_refresh_tooltip")
        )
        self.detach_button = Button(
            self.attached_control_frame,
            text=_("Detach Device"),
            command=self.detach_remote,
        )
        ToolTip(self.detach_button, _("attached_detach_tooltip"))

        self.attached_list_frame = Frame(self.root)
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
        attached_devices = list_attached_usb()
        for device in attached_devices:
            self.attached_listbox.insert("", "end", values=device)

        self.attached_list_label.grid(column=0, row=0, padx=10)
        self.attached_list_refresh_button.grid(column=1, row=0, padx=10)
        self.detach_button.grid(column=2, row=0, padx=10)

        self.attached_control_frame.grid(
            column=0, row=4, sticky="ew", pady=(10, 0)
        )
        self.attached_list_frame.grid(
            column=0, row=5, sticky="nsew", padx=10, pady=10
        )

    def check_secure_warning(self, var: BooleanVar):
        if not var.get():
            messagebox.showwarning(
                _("Warning"), 
                _("Disabling Secure mode is not recommended over the internet.")
            )

    def show_fingerprint(self):
        try:
            import ssl_tunnel
            cert_path, _key_path = ssl_tunnel.get_cert_paths()
            fp = ssl_tunnel.get_cert_fingerprint(cert_path)
            messagebox.showinfo(_("Certificate Fingerprint"), fp)
        except Exception as e:
            messagebox.showerror(_("Error"), str(e))
            
    def regenerate_cert(self):
        try:
            import ssl_tunnel
            import os
            cert_path, key_path = ssl_tunnel.get_cert_paths()
            if os.path.exists(cert_path):
                os.remove(cert_path)
            if os.path.exists(key_path):
                os.remove(key_path)
            ssl_tunnel.generate_self_signed_cert(cert_path, key_path)
            messagebox.showinfo(_("Success"), _("Certificate regenerated successfully. Please restart the server."))
        except Exception as e:
            messagebox.showerror(_("Error"), str(e))

    def refresh_local(self):
        """Refresh the local devices listbox with available USB devices."""
        local_devices = list_local_usb()
        self.local_listbox.delete(*self.local_listbox.get_children())
        for device in local_devices:
            self.local_listbox.insert("", "end", values=device)

    def restart_server(self):
        """Restart the local usbipd server on the specified port."""
        try:
            port = int(self.local_port_input.get())
        except ValueError:
            messagebox.showerror(_("Error"), _("Invalid port number"))
            return
        secure = self.local_secure_var.get()
        password = self.local_password_input.get()
        if secure and not password:
            messagebox.showerror(
                _("Error"), _("Password required for secure connection")
            )
            return
        init_usbip_server(port, secure, password)

    def refresh_remote(self):
        """Refresh remote devices listbox with the given server IP."""
        server_ip = self.remote_ip_input.get()
        try:
            port = int(self.remote_port_input.get())
        except ValueError:
            messagebox.showerror(_("Error"), _("Invalid port number"))
            return
        secure = self.remote_secure_var.get()
        password = self.remote_password_input.get()

        remote_devices = list_remote_usb(server_ip, port, secure, password)
        self.remote_listbox.delete(*self.remote_listbox.get_children())
        for device in remote_devices:
            self.remote_listbox.insert("", "end", values=device)

    def refresh_attached(self):
        """
        Refresh attached devices listbox with imported USB devices.
        """
        attached_devices = list_attached_usb()
        self.attached_listbox.delete(*self.attached_listbox.get_children())
        for device in attached_devices:
            self.attached_listbox.insert("", "end", values=device)

    # TODO these are both wrong
    def bind_local(self):
        """Bind the selected local USB device to make it exportable."""
        selection = self.local_listbox.selection()
        if not selection:
            print(_("no selection to bind"))
            messagebox.showerror(_("Error"), _("no selection to bind"))
            return

        bus_id = self.local_listbox.item(selection[0])["values"][0]

        result = bind_local_usb(bus_id)
        if result.returncode == 0:
            print(bus_id + _(" bound successfully"))

        time.sleep(0.5)
        self.refresh_local()

    def unbind_local(self):
        """Unbind the selected local USB device."""
        selection = self.local_listbox.selection()
        if not selection:
            print(_("no selection to unbind"))
            messagebox.showerror(_("Error"), _("no selection to unbind"))
            return

        bus_id = self.local_listbox.item(selection[0])["values"][0]

        result = unbind_local_usb(bus_id)
        if result.returncode == 0:
            print(bus_id + _(" unbound successfully"))

        time.sleep(0.5)
        self.refresh_local()

    def attach_remote(self):
        """Attach the selected remote USB device to the local machine."""
        server_ip = self.remote_ip_input.get()
        try:
            port = int(self.remote_port_input.get())
        except ValueError:
            messagebox.showerror(_("Error"), _("Invalid port number"))
            return
        selection = self.remote_listbox.selection()
        if not selection:
            print(_("no selection to attach"))
            messagebox.showerror(_("Error"), _("no selection to attach"))
            return

        secure = self.remote_secure_var.get()
        password = self.remote_password_input.get()

        print(server_ip)
        print(selection[0])
        print(selection)
        print(self.remote_listbox.item(selection[0]))
        bus_id = self.remote_listbox.item(selection[0])["values"][0]
        print(bus_id)
        result = attach_remote_usb(server_ip, bus_id, port, secure, password)
        print(result.returncode)
        # if result.returncode == 0:
        #     attached_devices[bus_id] = {
        #         'bus_id' : bus_id,
        #         'port' : len(attached_devices),
        #         'manufacturer' : manufacturer,
        #         'description' : description
        #     }
        # print(attached_devices)
        time.sleep(0.5)
        self.refresh_remote()
        self.refresh_local()
        self.refresh_attached()

    # TODO get selection
    def detach_remote(self):
        """Detach the selected imported USB device from the local machine."""
        selection = self.attached_listbox.selection()
        if not selection:
            print(_("no selection to detach"))
            messagebox.showerror(_("Error"), _("no selection to detach"))
            return  # no selected item
        print(selection)
        port = int(self.attached_listbox.item(selection[0])["values"][1])

        detach_remote_usb(port)

        time.sleep(0.5)
        self.refresh_remote()
        self.refresh_local()
        self.refresh_attached()

    def toggle_language(self):
        """Toggle the language (English/French Canadian) and restart."""

        current_lang = os.environ.get("LANGUAGE", "en")
        new_lang = "fr_CA" if current_lang != "fr_CA" else "en"
        os.environ["LANGUAGE"] = new_lang
        os.execv(sys.executable, [sys.executable] + sys.argv)


def start_app():
    """Initialize and launch the main Tkinter GUI application."""

    root = Tk()
    root.wm_title(_("USB/IP Peer"))
    root.geometry(DEFAULT_GEOMETRY)

    # Modernize UI with a better theme and fonts
    style = Style(root)
    if "clam" in style.theme_names():
        style.theme_use("clam")

    # Modern dark theme colors (Catppuccin inspired)
    bg_color = "#1e1e2e"
    fg_color = "#cdd6f4"
    input_bg = "#181825"
    button_bg = "#313244"
    button_active_bg = "#45475a"
    select_bg = "#89b4fa"
    select_fg = "#1e1e2e"
    border_color = "#313244"

    root.configure(bg=bg_color)

    style.configure(
        ".",
        background=bg_color,
        foreground=fg_color,
        troughcolor=bg_color,
        selectbackground=select_bg,
        selectforeground=select_fg,
        fieldbackground=input_bg,
        borderwidth=1,
        bordercolor=border_color,
    )

    style.configure(
        "Treeview",
        background=input_bg,
        fieldbackground=input_bg,
        foreground=fg_color,
        borderwidth=0,
        rowheight=28,
    )
    style.map(
        "Treeview",
        background=[("selected", select_bg)],
        foreground=[("selected", select_fg)],
    )

    style.configure(
        "Treeview.Heading",
        background=button_bg,
        foreground=fg_color,
        borderwidth=1,
        bordercolor=border_color,
        relief="flat",
    )
    style.map("Treeview.Heading", background=[("active", button_active_bg)])

    style.configure(
        "TButton",
        background=button_bg,
        foreground=fg_color,
        borderwidth=0,
        focuscolor=bg_color,
        relief="flat",
        padding=5,
    )
    style.map(
        "TButton",
        background=[("active", button_active_bg), ("pressed", select_bg)],
        foreground=[("pressed", select_fg)],
    )

    style.configure(
        "TCheckbutton",
        background=bg_color,
        foreground=fg_color,
        focuscolor=bg_color,
    )
    style.map(
        "TCheckbutton",
        background=[("active", bg_color), ("pressed", bg_color)],
        foreground=[("active", fg_color)],
        indicatorcolor=[("selected", select_bg), ("pressed", select_bg)],
    )

    style.configure(
        "TEntry",
        fieldbackground=input_bg,
        foreground=fg_color,
        bordercolor=border_color,
        lightcolor=bg_color,
        darkcolor=bg_color,
        padding=4,
        insertcolor=fg_color,
    )

    # Configure fonts to use the Ubuntu default font
    # This guarantees smooth fonts if the fonts-ubuntu package is installed.
    default_font = tkfont.nametofont("TkDefaultFont")
    default_font.configure(family="Ubuntu", size=11, weight="bold")

    heading_font = tkfont.nametofont("TkHeadingFont")
    heading_font.configure(family="Ubuntu", size=12, weight="bold")

    text_font = tkfont.nametofont("TkTextFont")
    text_font.configure(family="Ubuntu", size=11, weight="bold")

    style.configure(".", font="TkDefaultFont")
    style.configure("Treeview", font=("Ubuntu", 11, "bold"))
    style.configure("Treeview.Heading", font=("Ubuntu", 12, "bold"))

    loading_label = Label(
        root,
        text="Loading...\n--------------\nChargement...",
        font=("Sans Serif", 24),
    )
    loading_label.pack(expand=True)
    root.update()

    script_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "setup_usbip.sh",
    )
    if os.path.exists(script_path):
        modules = ["usbip_core", "usbip_host", "vhci_hcd"]
        if not all(os.path.exists(f"/sys/module/{mod}") for mod in modules):
            subprocess.run(["bash", script_path], check=False)

    loading_label.destroy()
    UsbIpGui(root)
    root.mainloop()
