"""Stub for ``usb.backend.libusb0`` — libusb 0.1.x backend for PyUSB."""

from collections.abc import Generator
from ctypes import Structure
from typing import Any

import usb.backend

__all__ = ["get_backend"]

# ---------------------------------------------------------------------------
# Low-level ctypes structure stubs (intentionally opaque)
# ---------------------------------------------------------------------------

class _PackPolicy:
    """Mixin that configures tight ctypes struct packing."""

    ...

class _usb_descriptor_header(Structure):
    """Generic USB descriptor header (bLength + bDescriptorType)."""

    ...

class _usb_string_descriptor(Structure):
    """Raw USB string descriptor."""

    ...

class _usb_endpoint_descriptor(Structure, _PackPolicy):
    """Raw USB endpoint descriptor."""

    ...

class _usb_interface_descriptor(Structure, _PackPolicy):
    """Raw USB interface descriptor."""

    ...

class _usb_interface(Structure, _PackPolicy):
    """Container holding all alternate settings for one interface."""

    ...

class _usb_config_descriptor(Structure, _PackPolicy):
    """Raw USB configuration descriptor."""

    ...

class _usb_device_descriptor(Structure, _PackPolicy):
    """Raw USB device descriptor."""

    ...

class _usb_device(Structure, _PackPolicy):
    """Opaque libusb 0.1 device structure."""

    ...

class _usb_bus(Structure, _PackPolicy):
    """Opaque libusb 0.1 bus structure."""

    ...

class _DeviceDescriptor:
    """Python-friendly view of a libusb 0.1 device descriptor."""

    bLength: Any
    """Total length of this descriptor in bytes."""

    bDescriptorType: Any
    """Descriptor type constant (always 0x01 for device descriptors)."""

    bcdUSB: Any
    """USB specification release number in BCD format."""

    bDeviceClass: Any
    """USB device class code."""

    bDeviceSubClass: Any
    """USB device sub-class code."""

    bDeviceProtocol: Any
    """USB device protocol code."""

    bMaxPacketSize0: Any
    """Maximum packet size for endpoint zero."""

    idVendor: Any
    """USB Vendor ID (VID)."""

    idProduct: Any
    """USB Product ID (PID)."""

    bcdDevice: Any
    """Device release number in BCD format."""

    iManufacturer: Any
    """Index of manufacturer string descriptor (0 = not present)."""

    iProduct: Any
    """Index of product string descriptor (0 = not present)."""

    iSerialNumber: Any
    """Index of serial-number string descriptor (0 = not present)."""

    bNumConfigurations: Any
    """Number of possible configurations."""

    address: Any
    """Device address on the bus."""

    bus: Any
    """Bus number the device is attached to."""

    port_number: Any
    """Physical port number."""

    port_numbers: Any
    """Tuple of port numbers from root hub to this device."""

    speed: Any
    """Negotiated connection speed."""

    def __init__(self, dev: Any) -> None:
        """Build a descriptor view from the raw libusb 0.1 *dev* structure."""
        ...

class _LibUSB(usb.backend.IBackend):
    """Concrete :class:`~usb.backend.IBackend` wrapping libusb 0.1."""

    def enumerate_devices(self) -> Generator[Any]:
        """Yield raw device handles for every device on every bus."""
        ...

    def get_device_descriptor(self, dev: Any) -> Any:
        """Return a :class:`_DeviceDescriptor` for *dev*."""
        ...

    def get_configuration_descriptor(self, dev: Any, config: Any) -> Any:
        """Return the configuration descriptor at index *config*."""
        ...

    def get_interface_descriptor(
        self, dev: Any, intf: Any, alt: Any, config: Any
    ) -> Any:
        """Return the interface descriptor for *intf*/*alt* in *config*."""
        ...

    def get_endpoint_descriptor(
        self, dev: Any, ep: Any, intf: Any, alt: Any, config: Any
    ) -> Any:
        """Return the endpoint descriptor for *ep* in *intf*/*alt*/*config*."""
        ...

    def open_device(self, dev: Any) -> Any:
        """Open *dev* and return a usb_dev_handle pointer."""
        ...

    def close_device(self, dev_handle: Any) -> None:
        """Close *dev_handle*."""
        ...

    def set_configuration(self, dev_handle: Any, config_value: Any) -> None:
        """Activate configuration *config_value* on *dev_handle*."""
        ...

    def get_configuration(self, dev_handle: Any) -> Any:
        """Return the active configuration value for *dev_handle*."""
        ...

    def set_interface_altsetting(
        self, dev_handle: Any, intf: Any, altsetting: Any
    ) -> None:
        """Set alternate setting *altsetting* for *intf* on *dev_handle*."""
        ...

    def claim_interface(self, dev_handle: Any, intf: Any) -> None:
        """Claim *intf* on *dev_handle*."""
        ...

    def release_interface(self, dev_handle: Any, intf: Any) -> None:
        """Release *intf* on *dev_handle*."""
        ...

    def bulk_write(
        self, dev_handle: Any, ep: Any, intf: Any, data: Any, timeout: Any
    ) -> Any:
        """Write *data* to bulk endpoint *ep*; return bytes written."""
        ...

    def bulk_read(
        self, dev_handle: Any, ep: Any, intf: Any, buff: Any, timeout: Any
    ) -> Any:
        """Read from bulk endpoint *ep* into *buff*; return bytes read."""
        ...

    def intr_write(
        self, dev_handle: Any, ep: Any, intf: Any, data: Any, timeout: Any
    ) -> Any:
        """Write *data* to interrupt endpoint *ep*."""
        ...

    def intr_read(
        self, dev_handle: Any, ep: Any, intf: Any, buff: Any, timeout: Any
    ) -> Any:
        """Read from interrupt endpoint *ep* into *buff*."""
        ...

    def iso_write(
        self, dev_handle: Any, ep: Any, intf: Any, data: Any, timeout: Any
    ) -> Any:
        """Write *data* to isochronous endpoint *ep*."""
        ...

    def iso_read(
        self, dev_handle: Any, ep: Any, intf: Any, buff: Any, timeout: Any
    ) -> Any:
        """Read from isochronous endpoint *ep* into *buff*."""
        ...

    def ctrl_transfer(
        self,
        dev_handle: Any,
        bmRequestType: Any,
        bRequest: Any,
        wValue: Any,
        wIndex: Any,
        data: Any,
        timeout: Any,
    ) -> Any:
        """Perform a control transfer on *dev_handle*."""
        ...

    def clear_halt(self, dev_handle: Any, ep: Any) -> None:
        """Clear the halt/stall condition on *ep*."""
        ...

    def reset_device(self, dev_handle: Any) -> None:
        """Issue a USB reset to the device."""
        ...

    def is_kernel_driver_active(self, dev_handle: Any, intf: Any) -> Any:
        """Return ``True`` if a kernel driver owns *intf*."""
        ...

    def detach_kernel_driver(self, dev_handle: Any, intf: Any) -> None:
        """Detach the kernel driver from *intf*."""
        ...

def get_backend(find_library: Any = None) -> Any:
    """Return a :class:`_LibUSB` backend instance, or ``None`` if unavailable."""
    ...
