"""Module for server.py."""

from tkinter import BooleanVar, Widget
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
import subprocess
import os
import sys
import time
import threading
from typing import List, Tuple

from .. import ssl_tunnel
from .common import get_translator, USBIPD_PORT, tunnel_state, ToolTip

_ = get_translator("server")

LOCAL_DEVICE_COLUMNS = [
    _("Bus ID"),
    _("State"),
    _("Manufacturer"),
    _("Description"),
]


def init_usbip_server(
    port: int = 3240,
    secure: bool = False,
    password: str = "",
    bind_host: str = "127.0.0.1",
):
    """Docstring for init_usbip_server."""
    subprocess.run(["sudo", "pkill", "usbipd"], check=False)
    if tunnel_state.server_process:
        try:
            tunnel_state.server_process.terminate()
            tunnel_state.server_process.wait()
        except OSError:
            pass
        tunnel_state.server_process = None

    if secure:
        target_port = port + 10000
        subprocess.run(
            ["sudo", "usbipd", "-D", "--tcp-port", str(target_port)],
            check=False,
        )

        def run_tunnel():
            with subprocess.Popen(
                [
                    sys.executable,
                    os.path.join(
                        os.path.dirname(os.path.dirname(__file__)),
                        "ssl_tunnel.py",
                    ),
                    "server",
                    "--listen-port",
                    str(port),
                    "--target-port",
                    str(target_port),
                    "--bind-host",
                    bind_host,
                    "--password",
                    password,
                ]
            ) as process:
                tunnel_state.server_process = process
                process.wait()

        threading.Thread(target=run_tunnel, daemon=True).start()
    else:
        subprocess.run(
            ["sudo", "usbipd", "-D", "--tcp-port", str(port)], check=False
        )


def parse_local_list(text: str) -> List[Tuple[str, str, str, str]]:
    """Docstring for parse_local_list."""
    if not text or not text.strip():
        return []

    rows: List[Tuple[str, str, str, str]] = []
    devices = text.strip().split("\n\n")
    for device in devices:
        lines = device.strip().split("\n")
        if len(lines) < 2:
            continue
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

        rows.append((bus_id, state, manufacturer, description))
    return rows


def list_local_usb() -> List[Tuple[str, str, str, str]]:
    """Docstring for list_local_usb."""
    result = subprocess.run(
        ["sudo", "usbip", "list", "--local"],
        capture_output=True,
        text=True,
        check=False,
    )
    return parse_local_list(result.stdout)


def bind_local_usb(bus_id: str):
    """Docstring for bind_local_usb."""
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
    """Docstring for unbind_local_usb."""
    result = subprocess.run(
        ["sudo", "usbip", "unbind", "--busid=" + bus_id],
        capture_output=True,
        text=True,
        check=False,
    )
    print(result.stdout)
    print(result.stderr)
    return result


class ServerTab:
    """Docstring for ServerTab."""

    def __init__(self, parent: Widget):
        """Docstring for __init__."""
        self.frame = Frame(parent)

        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)

        self.local_control_frame = Frame(self.frame)
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
            command=lambda: self.check_secure_warning(self.local_secure_var),
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

        self.local_list_frame = Frame(self.frame)
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

        self.local_bind_ip_label = Label(
            self.local_control_frame, text=_("Bind IP")
        )
        self.local_bind_ip_input = Entry(self.local_control_frame, width=12)
        self.local_bind_ip_input.insert(0, "127.0.0.1")

        self.local_list_label.grid(column=0, row=0, padx=10)
        self.local_port_label.grid(column=1, row=0, padx=(10, 0), sticky="e")
        self.local_port_input.grid(column=2, row=0, padx=(0, 10), sticky="w")
        self.local_bind_ip_label.grid(
            column=3, row=0, padx=(10, 0), sticky="e"
        )
        self.local_bind_ip_input.grid(
            column=4, row=0, padx=(0, 10), sticky="w"
        )
        self.local_secure_checkbox.grid(column=5, row=0, padx=5)
        self.local_password_input.grid(column=6, row=0, padx=5)
        self.local_server_restart_button.grid(column=7, row=0, padx=10)
        self.local_show_fingerprint_button.grid(column=8, row=0, padx=10)
        self.local_regen_cert_button.grid(column=9, row=0, padx=10)

        self.local_actions_frame.grid(
            column=1, row=1, columnspan=9, sticky="w", pady=(5, 0)
        )
        self.local_list_refresh_button.grid(column=0, row=0, padx=(10, 5))
        self.local_list_bind_button.grid(column=1, row=0, padx=5)
        self.local_list_unbind_button.grid(column=2, row=0, padx=5)

        self.local_control_frame.grid(
            column=0, row=0, sticky="ew", pady=(10, 0)
        )
        self.local_list_frame.grid(
            column=0, row=1, sticky="nsew", padx=10, pady=10
        )

    def check_secure_warning(self, var: BooleanVar):
        """Docstring for check_secure_warning."""
        if not var.get():
            messagebox.showwarning(_("Warning"), _("insecure_warning_msg"))

    def show_fingerprint(self):
        """Docstring for show_fingerprint."""
        try:
            cert_path, _key_path = ssl_tunnel.get_cert_paths()
            fp = ssl_tunnel.get_cert_fingerprint(cert_path)
            messagebox.showinfo(_("Certificate Fingerprint"), fp)
        except OSError as e:
            messagebox.showerror(_("Error"), str(e))

    def regenerate_cert(self):
        """Docstring for regenerate_cert."""
        try:
            cert_path, key_path = ssl_tunnel.get_cert_paths()
            if os.path.exists(cert_path):
                os.remove(cert_path)
            if os.path.exists(key_path):
                os.remove(key_path)
            ssl_tunnel.generate_self_signed_cert(cert_path, key_path)
            messagebox.showinfo(_("Success"), _("cert_regen"))
        except OSError as e:
            messagebox.showerror(_("Error"), str(e))

    def refresh_local(self):
        """Docstring for refresh_local."""
        local_devices = list_local_usb()
        self.local_listbox.delete(*self.local_listbox.get_children())
        for device in local_devices:
            self.local_listbox.insert("", "end", values=device)

    def restart_server(self):
        """Docstring for restart_server."""
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
        bind_host = self.local_bind_ip_input.get().strip() or "127.0.0.1"
        init_usbip_server(port, secure, password, bind_host)

    def bind_local(self):
        """Docstring for bind_local."""
        selection = self.local_listbox.selection()
        if not selection:
            messagebox.showerror(_("Error"), _("no selection to bind"))
            return
        bus_id = self.local_listbox.item(selection[0])["values"][0]
        bind_local_usb(str(bus_id))
        time.sleep(0.5)
        self.refresh_local()

    def unbind_local(self):
        """Docstring for unbind_local."""
        selection = self.local_listbox.selection()
        if not selection:
            messagebox.showerror(_("Error"), _("no selection to unbind"))
            return
        bus_id = self.local_listbox.item(selection[0])["values"][0]
        unbind_local_usb(str(bus_id))
        time.sleep(0.5)
        self.refresh_local()
