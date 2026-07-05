"""
A graphical user interface for managing and interacting with USB/IP devices.
"""

# requires python 3.8+
from tkinter import Tk
from tkinter.ttk import Treeview, Frame, Label, Entry, Button
import tkinter.messagebox as messagebox
import subprocess
import re
import time
from typing import List, Tuple
from urllib.parse import urlparse
from gettext import textdomain, bindtextdomain, gettext as _

APP_DOMAIN = "usbip-gui"

import os
from pathlib import Path

textdomain(APP_DOMAIN)
_local_localedir = Path(__file__).parent.parent / "share" / "locale"
if _local_localedir.exists():
    bindtextdomain(APP_DOMAIN, localedir=str(_local_localedir))
else:
    bindtextdomain(APP_DOMAIN, localedir="/usr/local/share/locale/")

DEVICE_COLUMNS = [_("bus_id"), _("manufacturer"), _("description")]
DEVICE_COLUMN_WIDTHS = [8, 20, 50]
ATTACHED_COLUMNS = [
    _("host"),
    _("port"),
    _("bus_id"),
    _("manufacturer"),
    _("description"),
]
ATTACHED_COLUMN_WIDTHS = [21, 3, 8, 20, 50]
USBIPD_PORT = 3240


def init_kernel_modules():
    """Load the required kernel modules for USB/IP."""
    subprocess.run(["sudo", "modprobe", "usbip_host"], check=False)
    subprocess.run(["sudo", "modprobe", "usbip_core"], check=False)
    subprocess.run(["sudo", "modprobe", "vhci_hcd"], check=False)


def init_usbip_server():
    """Initialize and start the usbipd server daemon."""
    # TODO log
    subprocess.run(["sudo", "usbipd"], check=False)


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


def parse_local_list(text: str) -> List[Tuple[str, str, str]]:
    """Parse the text output of 'usbip list --local'."""
    if not text or not text.strip():
        return []

    rows: List[Tuple[str, str, str]] = []
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

        rows.append(
            (
                bus_id,
                # bus_info[3],
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


def list_local_usb() -> List[Tuple[str, str, str]]:
    """Execute usbip to list local devices and return parsed rows."""
    result = subprocess.run(
        ["sudo", "usbip", "list", "--local"],
        capture_output=True,
        text=True,
        check=False,
    )
    return parse_local_list(result.stdout)


def list_remote_usb(server_ip: str) -> List[Tuple[str, str, str]]:
    """Execute usbip to list exportable devices on a remote server."""
    result = subprocess.run(
        ["sudo", "usbip", "list", "--remote=" + server_ip],
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


def attach_remote_usb(server_ip: str, bus_id: str):
    """Execute usbip to attach a remote device by bus ID."""
    result = subprocess.run(
        [
            "sudo",
            "usbip",
            "attach",
            "--remote=" + server_ip,
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


class UsbIpGui:
    def __init__(self, root: Tk):
        self.root = root
        self.root.wm_title(_("USB/IP Peer"))
        self.root.geometry("1002x842")

        # Remote devices
        self.remote_control_frame = Frame(self.root)
        self.remote_list_label = Label(
            self.remote_control_frame,
            text=_("Remote USB Devices for "),
        )
        self.remote_ip_input = Entry(self.remote_control_frame)
        self.remote_list_refresh_button = Button(
            self.remote_control_frame, text=_("Refresh"), command=self.refresh_remote
        )
        self.remote_list_attach_button = Button(
            self.remote_control_frame, text=_("Attach Device"), command=self.attach_remote
        )
        self.remote_listbox = Treeview(self.root, columns=DEVICE_COLUMNS, show="headings")

        for col in DEVICE_COLUMNS:
            self.remote_listbox.heading(col, text=col.title())
        
        remote_devices = list_remote_usb("127.0.0.1")
        for device in remote_devices:
            self.remote_listbox.insert("", "end", values=device)

        self.lang_button = Button(
            self.remote_control_frame, text="EN / FR", command=self.toggle_language
        )

        self.remote_list_label.grid(column=0, row=0, padx=10)
        self.remote_ip_input.grid(column=1, row=0, padx=10)
        self.remote_list_refresh_button.grid(column=2, row=0, padx=10)
        self.remote_list_attach_button.grid(column=3, row=0, padx=10)
        self.remote_control_frame.columnconfigure(4, weight=1)
        self.lang_button.grid(column=4, row=0, padx=10, sticky="e")

        self.remote_control_frame.grid(column=0, row=0, sticky="ew", pady=10)
        self.remote_listbox.grid(column=0, row=1, sticky="ew", pady=10)

        # Local devices
        self.local_control_frame = Frame(self.root)
        self.local_list_label = Label(self.local_control_frame, text=_("Local USB Devices"))
        self.local_list_refresh_button = Button(
            self.local_control_frame, text=_("Refresh"), command=self.refresh_local
        )
        self.local_list_bind_button = Button(
            self.local_control_frame, text=_("Bind Device"), command=self.bind_local
        )
        self.local_list_unbind_button = Button(
            self.local_control_frame, text=_("Unbind Device"), command=self.unbind_local
        )
        self.local_listbox = Treeview(self.root, columns=DEVICE_COLUMNS, show="headings")

        for col in DEVICE_COLUMNS:
            self.local_listbox.heading(col, text=col.title())

        local_devices = list_local_usb()
        for device in local_devices:
            self.local_listbox.insert("", "end", values=device)

        self.local_list_label.grid(column=0, row=0, padx=10)
        self.local_list_refresh_button.grid(column=1, row=0, padx=10)
        self.local_list_bind_button.grid(column=3, row=0, padx=10)
        self.local_list_unbind_button.grid(column=4, row=0, padx=10)

        self.local_control_frame.grid(column=0, row=2, sticky="ew", pady=10)
        self.local_listbox.grid(column=0, row=3, sticky="ew", pady=10)

        # Attached devices
        self.attached_control_frame = Frame(self.root)
        self.attached_list_label = Label(
            self.attached_control_frame, text=_("Attached Devices")
        )
        self.attached_list_refresh_button = Button(
            self.attached_control_frame, text=_("Refresh"), command=self.refresh_attached
        )
        self.detach_button = Button(
            self.attached_control_frame, text=_("Detach Device"), command=self.detach_remote
        )
        self.attached_listbox = Treeview(self.root, columns=ATTACHED_COLUMNS, show="headings")

        for col in ATTACHED_COLUMNS:
            self.attached_listbox.heading(col, text=col.title())

        attached_devices = list_attached_usb()
        for device in attached_devices:
            self.attached_listbox.insert("", "end", values=device)

        self.attached_list_label.grid(column=0, row=0, padx=10)
        self.attached_list_refresh_button.grid(column=1, row=0, padx=10)
        self.detach_button.grid(column=2, row=0, padx=10)

        self.attached_control_frame.grid(column=0, row=4, sticky="ew", pady=10)
        self.attached_listbox.grid(column=0, row=5, sticky="ew", pady=10)


    def refresh_local(self):
        """Refresh the local devices listbox with available USB devices."""
        local_devices = list_local_usb()
        self.local_listbox.delete(*self.local_listbox.get_children())
        for device in local_devices:
            self.local_listbox.insert("", "end", values=device)


    def refresh_remote(self):
        """Refresh the remote devices listbox by querying the given server IP."""
        server_ip = self.remote_ip_input.get()
        remote_devices = list_remote_usb(server_ip)
        self.remote_listbox.delete(*self.remote_listbox.get_children())
        for device in remote_devices:
            self.remote_listbox.insert("", "end", values=device)


    def refresh_attached(self):
        """
        Refresh the attached devices listbox with currently imported USB devices.
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


    def attach_remote(self):
        """Attach the selected remote USB device to the local machine."""
        server_ip = self.remote_ip_input.get()
        selection = self.remote_listbox.selection()
        if not selection:
            print(_("no selection to attach"))
            messagebox.showerror(_("Error"), _("no selection to attach"))
            return
        print(server_ip)
        print(selection[0])
        print(selection)
        print(self.remote_listbox.item(selection[0]))
        bus_id = self.remote_listbox.item(selection[0])["values"][0]
        print(bus_id)
        result = attach_remote_usb(server_ip, bus_id)
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
        """Toggle the interface language between English and French Canadian and restart."""
        import os
        import sys
        current_lang = os.environ.get("LANGUAGE", "en")
        new_lang = "fr_CA" if current_lang != "fr_CA" else "en"
        os.environ["LANGUAGE"] = new_lang
        os.execv(sys.executable, [sys.executable] + sys.argv)


def start_app():
    """Initialize and launch the main Tkinter GUI application."""
    import os
    
    root = Tk()
    root.wm_title(_("USB/IP Peer"))
    root.geometry("1002x842")
    
    loading_label = Label(root, text="Loading / Chargement...", font=("Arial", 24))
    loading_label.pack(expand=True)
    root.update()

    script_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "setup_usbip.sh"
    )
    if os.path.exists(script_path):
        subprocess.run(["bash", script_path], check=False)

    loading_label.destroy()
    UsbIpGui(root)
    root.mainloop()
