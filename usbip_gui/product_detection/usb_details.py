"""Probe USB descriptor strings for a given bus ID.

This script is intended to be run as a subprocess (potentially with elevated
privileges) by :func:`usbip_gui.gui.server._read_local_usb_descriptor_details`.

Usage::

    python usb_details.py <bus-id>

Prints a JSON object with the keys ``manufacturer``, ``product``, and
``error`` to stdout.
"""

import json
import sys
from pathlib import Path
from typing import Optional, Tuple

import usb.core
import usb.util

PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)  # pragma: no cover

# pylint: disable=wrong-import-position
from usbip_gui.product_detection.heuristics import (  # noqa: E402
    is_generic_manufacturer,
)


def parse_bus_id(bus_id: str) -> Tuple[Optional[int], Tuple[int, ...]]:
    """Split a bus ID string (e.g. ``1-2.3``) into bus number and port path."""
    bus_part, separator, port_part = bus_id.partition("-")
    if not separator:
        return None, ()

    try:
        bus_num = int(bus_part)
        port_numbers: Tuple[int, ...] = tuple(
            int(port) for port in port_part.split(".") if port
        )
    except (ValueError, OSError):
        return None, ()

    return bus_num, port_numbers


def matches_device(device: usb.core.Device, bus_id: str) -> bool:
    """Return True when *device* corresponds to the given *bus_id*."""
    bus_num, port_numbers = parse_bus_id(bus_id)
    if bus_num is None or getattr(device, "bus", None) != bus_num:
        return False

    device_ports: Tuple[int, ...] = tuple(
        getattr(device, "port_numbers", None) or ()
    )
    if device_ports:
        return device_ports == port_numbers

    device_port: Optional[int] = getattr(device, "port_number", None)
    if device_port is not None:
        return (device_port,) == port_numbers

    return False


def get_string(device: usb.core.Device, index: int) -> str:
    """Return the USB descriptor string at *index*, or an empty string."""
    if not index:
        return ""

    try:
        return usb.util.get_string(device, index) or ""
    except Exception:  # pylint: disable=broad-exception-caught
        return ""


def _resolve_inf_string(raw: str) -> str:
    """Strip leading INF resource reference from a Windows registry value.

    Many Windows registry strings use the format
    ``@oem5.inf,%key%;Actual String`` or simply ``Actual String``.
    This function returns only the human-readable trailing part.
    """
    return raw.rsplit(";", 1)[-1].strip()


def get_strings_from_registry(vid: int, pid: int) -> Tuple[str, str]:
    """Read manufacturer and product from the Windows registry.

    Used as a fallback on Windows when the device is claimed by a kernel
    driver (e.g. usbprint.sys for printers) that prevents pyusb / libusb
    from opening the device to read USB string descriptors.

    Returns a ``(manufacturer, product)`` tuple; either value may be an
    empty string if the registry entry is absent.
    """
    if sys.platform != "win32":
        return "", ""
    import winreg  # pyright: ignore[reportMissingModuleSource]  # pylint: disable=import-outside-toplevel,import-error  # noqa: E501

    base = (
        f"SYSTEM\\CurrentControlSet\\Enum\\USB"
        f"\\VID_{vid:04X}&PID_{pid:04X}"
    )

    def _qv(inst: "winreg.HKEYType", name: str) -> str:
        try:
            val = winreg.QueryValueEx(inst, name)[0]
            return _resolve_inf_string(str(val))
        except OSError:
            return ""

    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base) as key:
            index = 0
            while True:
                try:
                    instance = winreg.EnumKey(key, index)
                except OSError:
                    break
                try:
                    with winreg.OpenKey(key, instance) as inst:
                        mfg = _qv(inst, "Mfg")
                        desc = _qv(inst, "DeviceDesc")
                        bus_desc = _qv(inst, "BusReportedDeviceDesc")

                        # If the driver is generic, BusReportedDeviceDesc
                        # is more accurate than DeviceDesc
                        if (
                            is_generic_manufacturer(mfg)
                            and bus_desc
                            and not bus_desc.lower().startswith("usb ")
                        ):
                            if is_generic_manufacturer(desc):
                                first_word = bus_desc.split(" ")[0]
                                if first_word.lower() not in (
                                    "usb",
                                    "generic",
                                    "unknown",
                                    "",
                                ):
                                    mfg = first_word
                                desc = bus_desc
                        else:
                            if bus_desc and desc.lower().startswith("usb "):
                                desc = bus_desc

                        if mfg or desc:
                            return mfg, desc
                except OSError:
                    pass
                index += 1
    except OSError:
        pass
    return "", ""


def main() -> None:
    """Entry point: read descriptor strings."""
    payload: dict[str, str] = {"manufacturer": "", "product": "", "error": ""}

    if len(sys.argv) == 3 and sys.argv[1] == "--vid-pid":
        if sys.platform != "win32":
            payload["error"] = "Registry lookup only supported on Windows."
            print(json.dumps(payload))
            return

        try:
            vid_str, pid_str = sys.argv[2].split(":")
            vid = int(vid_str, 16)
            pid = int(pid_str, 16)
            mfg, prod = get_strings_from_registry(vid, pid)
            payload["manufacturer"] = mfg
            payload["product"] = prod
        except Exception as exc:  # pylint: disable=broad-exception-caught
            payload["error"] = str(exc)

        print(json.dumps(payload))
        return

    bus_id = sys.argv[1]

    try:
        device = usb.core.find(
            custom_match=lambda d: matches_device(d, bus_id)
        )
        if device is None:
            payload["error"] = f"Could not find USB device {bus_id}."
        else:
            manufacturer = get_string(
                device, getattr(device, "iManufacturer", 0)
            )
            product = get_string(device, getattr(device, "iProduct", 0))

            # On Windows, devices claimed by kernel drivers (printers,
            # audio, etc.) block libusb from reading string descriptors.
            # Fall back to the Windows registry which already holds the
            # strings installed by the device driver INF.
            if sys.platform == "win32" and not manufacturer and not product:
                dev_vid: Optional[int] = getattr(device, "idVendor", None)
                dev_pid: Optional[int] = getattr(device, "idProduct", None)
                if dev_vid is not None and dev_pid is not None:
                    manufacturer, product = get_strings_from_registry(
                        dev_vid, dev_pid
                    )

            payload["manufacturer"] = manufacturer
            payload["product"] = product
    except usb.core.NoBackendError:
        payload["error"] = "No PyUSB backend found."
    except usb.core.USBError as exc:
        payload["error"] = f"USB error ({exc.errno}): {exc.strerror}"
    except Exception as exc:  # pylint: disable=broad-exception-caught
        payload["error"] = str(exc)

    print(json.dumps(payload))


if __name__ == "__main__":
    main()
