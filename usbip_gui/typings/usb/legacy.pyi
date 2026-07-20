"""Stub for ``usb.legacy`` — compatibility shim for the old PyUSB 0.x API.

This module re-implements the PyUSB 0.x object model on top of the modern
PyUSB 1.x core so that code written for the old API continues to work.
"""

from typing import Any, Optional

import usb._objfinalizer as _objfinalizer
import usb.core as core

USBError = core.USBError
"""Re-export of :class:`usb.core.USBError` for backward compatibility."""

# ---------------------------------------------------------------------------
# USB class codes (mirrored from the old PyUSB 0.x constants)
# ---------------------------------------------------------------------------

CLASS_AUDIO: int
"""USB Audio device class code."""

CLASS_COMM: int
"""USB Communications device class code."""

CLASS_DATA: int
"""USB Data device class code."""

CLASS_HID: int
"""USB Human Interface Device class code."""

CLASS_HUB: int
"""USB Hub class code."""

CLASS_MASS_STORAGE: int
"""USB Mass Storage device class code."""

CLASS_PER_INTERFACE: int
"""Class code indicating class is defined per interface."""

CLASS_PRINTER: int
"""USB Printer device class code."""

CLASS_WIRELESS_CONTROLLER: int
"""USB Wireless Controller class code."""

CLASS_VENDOR_SPEC: int
"""Vendor-specific class code."""

# ---------------------------------------------------------------------------
# Descriptor type codes
# ---------------------------------------------------------------------------

DT_CONFIG: int
"""Descriptor type: Configuration."""

DT_CONFIG_SIZE: int
"""Size of a configuration descriptor in bytes."""

DT_DEVICE: int
"""Descriptor type: Device."""

DT_DEVICE_SIZE: int
"""Size of a device descriptor in bytes."""

DT_ENDPOINT: int
"""Descriptor type: Endpoint."""

DT_ENDPOINT_AUDIO_SIZE: int
"""Size of an audio endpoint descriptor in bytes."""

DT_ENDPOINT_SIZE: int
"""Size of a standard endpoint descriptor in bytes."""

DT_HID: int
"""Descriptor type: HID."""

DT_HUB: int
"""Descriptor type: Hub."""

DT_HUB_NONVAR_SIZE: int
"""Size of the non-variable portion of a hub descriptor."""

DT_INTERFACE: int
"""Descriptor type: Interface."""

DT_INTERFACE_SIZE: int
"""Size of an interface descriptor in bytes."""

DT_PHYSICAL: int
"""Descriptor type: Physical."""

DT_REPORT: int
"""Descriptor type: HID Report."""

DT_STRING: int
"""Descriptor type: String."""

# ---------------------------------------------------------------------------
# Endpoint constants
# ---------------------------------------------------------------------------

ENDPOINT_ADDRESS_MASK: int
"""Mask to extract the endpoint address from bmAttributes."""

ENDPOINT_DIR_MASK: int
"""Mask to extract the direction bit from an endpoint address."""

ENDPOINT_IN: int
"""Endpoint direction: device-to-host (0x80)."""

ENDPOINT_OUT: int
"""Endpoint direction: host-to-device (0x00)."""

ENDPOINT_TYPE_BULK: int
"""Transfer type: Bulk."""

ENDPOINT_TYPE_CONTROL: int
"""Transfer type: Control."""

ENDPOINT_TYPE_INTERRUPT: int
"""Transfer type: Interrupt."""

ENDPOINT_TYPE_ISOCHRONOUS: int
"""Transfer type: Isochronous."""

ENDPOINT_TYPE_MASK: int
"""Mask to extract transfer type bits from bmAttributes."""

# ---------------------------------------------------------------------------
# Miscellaneous constants
# ---------------------------------------------------------------------------

ERROR_BEGIN: int
"""Base error-code value for USB errors."""

MAXALTSETTING: int
"""Maximum number of alternate settings per interface."""

MAXCONFIG: int
"""Maximum number of configurations per device."""

MAXENDPOINTS: int
"""Maximum number of endpoints per interface."""

MAXINTERFACES: int
"""Maximum number of interfaces per configuration."""

PROTOCOL_BLUETOOTH_PRIMARY_CONTROLLER: int
"""Protocol code for a Bluetooth primary controller."""

# ---------------------------------------------------------------------------
# bmRequestType field constants
# ---------------------------------------------------------------------------

RECIP_DEVICE: int
"""Request recipient: Device."""

RECIP_ENDPOINT: int
"""Request recipient: Endpoint."""

RECIP_INTERFACE: int
"""Request recipient: Interface."""

RECIP_OTHER: int
"""Request recipient: Other."""

REQ_CLEAR_FEATURE: int
"""Standard request: ClearFeature."""

REQ_GET_CONFIGURATION: int
"""Standard request: GetConfiguration."""

REQ_GET_DESCRIPTOR: int
"""Standard request: GetDescriptor."""

REQ_GET_INTERFACE: int
"""Standard request: GetInterface."""

REQ_GET_STATUS: int
"""Standard request: GetStatus."""

REQ_SET_ADDRESS: int
"""Standard request: SetAddress."""

REQ_SET_CONFIGURATION: int
"""Standard request: SetConfiguration."""

REQ_SET_DESCRIPTOR: int
"""Standard request: SetDescriptor."""

REQ_SET_FEATURE: int
"""Standard request: SetFeature."""

REQ_SET_INTERFACE: int
"""Standard request: SetInterface."""

REQ_SYNCH_FRAME: int
"""Standard request: SynchFrame."""

SUBCLASS_RF_CONTROLLER: int
"""Sub-class code for an RF controller."""

TYPE_CLASS: int
"""Request type: Class."""

TYPE_RESERVED: int
"""Request type: Reserved."""

TYPE_STANDARD: int
"""Request type: Standard."""

TYPE_VENDOR: int
"""Request type: Vendor."""

# ---------------------------------------------------------------------------
# Legacy object model
# ---------------------------------------------------------------------------

class Endpoint:
    """USB endpoint descriptor wrapper (PyUSB 0.x compatible)."""

    address: Any
    """Endpoint address byte (includes direction bit)."""

    interval: Any
    """Polling interval in frame counts (for interrupt/isochronous endpoints)."""

    maxPacketSize: Any
    """Maximum packet size in bytes."""

    type: Any
    """Transfer type (one of the ``ENDPOINT_TYPE_*`` constants)."""

    def __init__(self, ep: Any) -> None:
        """Construct from a raw endpoint descriptor *ep*."""
        ...

class Interface:
    """USB interface descriptor wrapper (PyUSB 0.x compatible)."""

    alternateSetting: Any
    """Alternate setting number for this interface."""

    interfaceNumber: Any
    """Interface number."""

    iInterface: Any
    """Index of the interface string descriptor."""

    interfaceClass: Any
    """USB class code for this interface."""

    interfaceSubClass: Any
    """USB sub-class code for this interface."""

    interfaceProtocol: Any
    """USB protocol code for this interface."""

    endpoints: Any
    """List of :class:`Endpoint` objects on this interface."""

    def __init__(self, intf: Any) -> None:
        """Construct from a raw interface descriptor *intf*."""
        ...

class Configuration:
    """USB configuration descriptor wrapper (PyUSB 0.x compatible)."""

    iConfiguration: Any
    """Index of the configuration string descriptor."""

    maxPower: Any
    """Maximum power consumption in milliamps."""

    remoteWakeup: Any
    """Non-zero if remote wakeup is supported."""

    selfPowered: Any
    """Non-zero if the device is self-powered in this configuration."""

    totalLength: Any
    """Total length of the configuration descriptor and sub-descriptors."""

    value: Any
    """Configuration value used to select this configuration."""

    interfaces: Any
    """Nested list of :class:`Interface` objects."""

    def __init__(self, cfg: Any) -> None:
        """Construct from a raw configuration descriptor *cfg*."""
        ...

class DeviceHandle(_objfinalizer.AutoFinalizedObject):
    """An open handle to a USB device (PyUSB 0.x compatible)."""

    dev: Any
    """The :class:`Device` this handle was opened from."""

    def __init__(self, dev: Any) -> None:
        """Open *dev* and store the resulting handle."""
        ...

    def bulkWrite(self, endpoint: Any, buffer: Any, timeout: int = 100) -> Any:
        """Write *buffer* to bulk *endpoint*; return bytes written."""
        ...

    def bulkRead(self, endpoint: Any, size: Any, timeout: int = 100) -> Any:
        """Read *size* bytes from bulk *endpoint*; return the data."""
        ...

    def interruptWrite(
        self, endpoint: Any, buffer: Any, timeout: int = 100
    ) -> Any:
        """Write *buffer* to interrupt *endpoint*."""
        ...

    def interruptRead(
        self, endpoint: Any, size: Any, timeout: int = 100
    ) -> Any:
        """Read *size* bytes from interrupt *endpoint*."""
        ...

    def controlMsg(
        self,
        requestType: Any,
        request: Any,
        buffer: Any,
        value: int = 0,
        index: int = 0,
        timeout: int = 100,
    ) -> Any:
        """Send a control message; return the response data."""
        ...

    def clearHalt(self, endpoint: Any) -> None:
        """Clear the halt/stall condition on *endpoint*."""
        ...

    def claimInterface(self, interface: Any) -> None:
        """Claim *interface* for exclusive use."""
        ...

    def releaseInterface(self) -> None:
        """Release the currently claimed interface."""
        ...

    def reset(self) -> None:
        """Issue a USB reset to the device."""
        ...

    def resetEndpoint(self, endpoint: Any) -> None:
        """Reset *endpoint* to its default state."""
        ...

    def setConfiguration(self, configuration: Any) -> None:
        """Activate *configuration* on the device."""
        ...

    def setAltInterface(self, alternate: Any) -> None:
        """Switch to alternate interface setting *alternate*."""
        ...

    def getString(self, index: Any, length: Any, langid: Any = None) -> Any:
        """Read and return a string descriptor by *index* and *langid*."""
        ...

    def getDescriptor(
        self, desc_type: Any, desc_index: Any, length: Any, endpoint: int = -1
    ) -> Any:
        """Fetch a descriptor of *desc_type* and *desc_index* from the device."""
        ...

    def detachKernelDriver(self, interface: Any) -> None:
        """Detach the kernel driver from *interface*."""
        ...

class Device:
    """USB device descriptor wrapper (PyUSB 0.x compatible)."""

    deviceClass: Any
    """USB device class code."""

    deviceSubClass: Any
    """USB device sub-class code."""

    deviceProtocol: Any
    """USB device protocol code."""

    deviceVersion: Any
    """Device firmware release number in BCD format."""

    devnum: Any
    """Device number on the bus."""

    filename: str
    """Device node filename (Linux: ``/dev/bus/usb/...``)."""

    iManufacturer: Any
    """Index of the manufacturer string descriptor."""

    iProduct: Any
    """Index of the product string descriptor."""

    iSerialNumber: Any
    """Index of the serial-number string descriptor."""

    idProduct: Any
    """USB Product ID (PID)."""

    idVendor: Any
    """USB Vendor ID (VID)."""

    maxPacketSize: Any
    """Maximum packet size for endpoint zero."""

    usbVersion: Any
    """USB specification release number in BCD format."""

    configurations: Any
    """List of :class:`Configuration` objects for this device."""

    dev: Any
    """Underlying :mod:`usb.core` device object."""

    def __init__(self, dev: Any) -> None:
        """Construct from a :class:`usb.core.Device` instance *dev*."""
        ...

    def open(self) -> DeviceHandle:
        """Open the device and return a :class:`DeviceHandle`."""
        ...

class Bus:
    """Represents a USB bus (PyUSB 0.x compatible)."""

    dirname: str
    """Directory path for the bus's device nodes."""

    devices: Any
    """List of :class:`Device` objects on this bus."""

    location: Any
    """Bus number."""

    def __init__(self, devices: Any) -> None:
        """Construct by wrapping a list of :class:`Device` objects."""
        ...

def busses() -> Any:
    """Return an iterable of :class:`Bus` objects for all connected buses."""
    ...
