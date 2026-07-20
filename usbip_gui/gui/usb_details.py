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
from typing import Optional, Tuple

import usb.core
import usb.util


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
    except ValueError:
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


def main() -> None:
    """Entry point: read descriptor strings for the bus ID in sys.argv[1]."""
    bus_id = sys.argv[1]
    payload: dict[str, str] = {"manufacturer": "", "product": "", "error": ""}

    try:
        device: Optional[usb.core.Device] = None
        for candidate in usb.core.find(find_all=True) or []:
            if matches_device(candidate, bus_id):
                device = candidate
                break

        if device is None:
            payload["error"] = f"Could not find USB device {bus_id}."
        else:
            payload["manufacturer"] = get_string(
                device, getattr(device, "iManufacturer", 0)
            )
            payload["product"] = get_string(
                device, getattr(device, "iProduct", 0)
            )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        payload["error"] = str(exc)

    print(json.dumps(payload))


if __name__ == "__main__":
    main()
