"""Stub for ``usb.core`` — PyUSB core device model.

This module exposes the primary USB abstractions: :class:`Device`,
:class:`Configuration`, :class:`Interface`, :class:`Endpoint`, and the
top-level :func:`find` function.
"""

from typing import Any, Callable, List, Literal, Optional, TypeVar, overload

import usb._objfinalizer as _objfinalizer

__all__ = [
    "Device",
    "Configuration",
    "Interface",
    "Endpoint",
    "USBError",
    "USBTimeoutError",
    "NoBackendError",
    "find",
    "show_devices",
]

_F = TypeVar("_F", bound=object)

def synchronized(fn: _F) -> _F:
    """Decorator that wraps *fn* with the device's threading lock."""
    ...

class _DescriptorInfo(str):
    """String subclass used to annotate descriptor information."""

    ...

class _ResourceManager:
    """Manages the lifecycle of an open USB device handle."""

    backend: Any
    """The backend (libusb0 / libusb1 / openusb) handling this device."""

    dev: Any
    """Raw device descriptor obtained from the backend."""

    handle: Any
    """Open device handle; ``None`` when the device is not open."""

    lock: Any
    """Threading lock serialising access to the device handle."""

    def __init__(self, dev: Any, backend: Any) -> None:
        """Initialise with a raw *dev* descriptor and a *backend* instance."""
        ...

    @synchronized
    def managed_open(self) -> Any:
        """Open the device handle if not already open; return it."""
        ...

    @synchronized
    def managed_close(self) -> None:
        """Close the device handle if open."""
        ...
    index: Any
    bConfigurationValue: int

    @synchronized
    def managed_set_configuration(self, device: Any, config: Any) -> None:
        """
        Activate *config* on *device*, tracking it in the resource manager.
        """
        ...

    @synchronized
    def managed_claim_interface(self, device: Any, intf: Any) -> None:
        """Claim *intf* for exclusive use, recording it for later release."""
        ...

    @synchronized
    def managed_release_interface(self, device: Any, intf: Any) -> None:
        """Release a previously claimed *intf*."""
        ...

    @synchronized
    def managed_set_interface(self, device: Any, intf: Any, alt: Any) -> None:
        """Switch *intf* to alternate setting *alt*."""
        ...

    @synchronized
    def setup_request(self, device: Any, endpoint: Any) -> Any:
        """Prepare a transfer request for *endpoint* on *device*."""
        ...

    @synchronized
    def get_interface_and_endpoint(
        self, device: Any, endpoint_address: Any
    ) -> Any:
        """Return the (interface, endpoint) pair for *endpoint_address*."""
        ...

    @synchronized
    def get_active_configuration(self, device: Any) -> Any:
        """Return the currently active :class:`Configuration` on *device*."""
        ...

    @synchronized
    def release_all_interfaces(self, device: Any) -> None:
        """Release every claimed interface on *device*."""
        ...

    @synchronized
    def dispose(self, device: Any, close_handle: bool = True) -> None:
        """Release all interfaces and optionally close the device handle."""
        ...

class USBError(IOError):
    """Raised for any USB-level communication error."""

    backend_error_code: Any
    """Backend-specific error code (e.g. a libusb error constant)."""

    def __init__(
        self,
        strerror: Any,
        error_code: Optional[Any] = None,
        errno: Optional[Any] = None,
    ) -> None:
        """Create a :class:`USBError` with *strerror* and optional codes."""
        ...

class USBTimeoutError(USBError):
    """Raised when a USB transfer times out."""

    ...

class NoBackendError(ValueError):
    """Raised when no suitable USB backend (libusb) can be found."""

    ...

class Endpoint:
    """Represents a single USB endpoint within an interface."""

    device: Any
    """The :class:`Device` this endpoint belongs to."""

    index: Any
    """Index of this endpoint within its interface descriptor."""

    def __init__(
        self,
        device: Any,
        endpoint: Any,
        interface: int = 0,
        alternate_setting: int = 0,
        configuration: int = 0,
    ) -> None:
        """
        Construct an :class:`Endpoint` from its parent *device* and
        descriptor index.
        """
        ...

    def write(self, data: Any, timeout: Optional[Any] = None) -> Any:
        """
        Write *data* to this endpoint; return the number of bytes written.
        """
        ...

    def read(self, size_or_buffer: Any, timeout: Optional[Any] = None) -> Any:
        """Read from this endpoint into *size_or_buffer*; return bytes read."""
        ...

    def clear_halt(self) -> None:
        """Clear the halt/stall condition on this endpoint."""
        ...

class Interface:
    """
    Represents a USB interface (a logical function within a configuration).
    """

    device: Any
    """The :class:`Device` this interface belongs to."""

    alternate_index: Any
    """Index of the active alternate setting."""

    index: Any
    """Interface number."""

    configuration: Any
    """Configuration value this interface belongs to."""

    def __init__(
        self,
        device: Any,
        interface: int = 0,
        alternate_setting: int = 0,
        configuration: int = 0,
    ) -> None:
        """
        Construct an :class:`Interface` from its parent *device* and indices.
        """
        ...

    def endpoints(self) -> Any:
        """
        Return an iterable of :class:`Endpoint` objects on this interface.
        """
        ...

    def set_altsetting(self) -> None:
        """Activate this interface's alternate setting on the device."""
        ...

    def __iter__(self) -> Any:
        """Iterate over the endpoints in this interface."""
        ...

    def __getitem__(self, index: Any) -> Any:
        """Return the endpoint at position *index*."""
        ...

class Configuration:
    """Represents a USB device configuration."""

    device: Any
    """The :class:`Device` this configuration belongs to."""

    index: Any
    """Zero-based index of this configuration in the device descriptor."""

    def __init__(self, device: Any, configuration: int = 0) -> None:
        """
        Construct a :class:`Configuration` for
        *device* at *configuration* index.
        """
        ...

    def interfaces(self) -> Any:
        """
        Return an iterable of :class:`Interface` objects in this configuration.
        """
        ...

    def set(self) -> None:
        """Activate this configuration on the device."""
        ...

    def __iter__(self) -> Any:
        """Iterate over the interfaces in this configuration."""
        ...

    def __getitem__(self, index: Any) -> Any:
        """Return the interface at position *index*."""
        ...

class Device(_objfinalizer.AutoFinalizedObject):
    """Represents a physical USB device attached to the host.

    Provides high-level methods for I/O (control, bulk, interrupt,
    isochronous) and device management (configuration, interface claiming).
    """

    bus: Any
    """USB bus number the device is attached to."""

    address: Any
    """Device address on the bus."""

    port_number: Any
    """Physical port number the device is plugged into."""

    port_numbers: Any
    """Tuple of port numbers from the root hub to this device."""

    speed: Any
    """Negotiated connection speed (one of the ``SPEED_*`` constants)."""

    idVendor: int
    """USB Vendor ID (VID)."""

    idProduct: int
    """USB Product ID (PID)."""

    iManufacturer: int
    """Index of the manufacturer string descriptor (0 = not present)."""

    iProduct: int
    """Index of the product string descriptor (0 = not present)."""

    default_timeout: Any
    """Default transfer timeout in milliseconds."""

    def __init__(self, dev: Any, backend: Any) -> None:
        """Initialise from a raw *dev* descriptor and a *backend* instance."""
        ...

    def __eq__(self, other: object) -> bool:
        """Return ``True`` if *other* refers to the same physical device."""
        ...

    def __hash__(self) -> int:
        """Return a hash based on bus and address for use in sets/dicts."""
        ...

    def configurations(self) -> Any:
        """Return an iterable of :class:`Configuration` objects."""
        ...

    @property
    def langids(self) -> Any:
        """Supported string-descriptor language IDs (tuple of ints)."""
        ...

    @property
    def serial_number(self) -> Any:
        """Device serial number string, or ``None`` if unavailable."""
        ...

    @property
    def product(self) -> Any:
        """Product name string read from the USB string descriptor."""
        ...

    @property
    def parent(self) -> Any:
        """Parent :class:`Device` (hub), or ``None`` for root devices."""
        ...

    @property
    def manufacturer(self) -> Any:
        """Manufacturer name string read from the USB string descriptor."""
        ...

    @property
    def backend(self) -> Any:
        """The backend instance managing this device."""
        ...

    def set_configuration(self, configuration: Optional[Any] = None) -> None:
        """Activate *configuration* (or the first one if ``None``)."""
        ...

    def get_active_configuration(self) -> Any:
        """Return the currently active :class:`Configuration`."""
        ...

    def set_interface_altsetting(
        self,
        interface: Optional[Any] = None,
        alternate_setting: Optional[Any] = None,
    ) -> None:
        """Select an alternate setting for the specified interface."""
        ...

    def clear_halt(self, ep: Any) -> None:
        """Clear the halt/stall condition on endpoint *ep*."""
        ...

    def reset(self) -> None:
        """Issue a USB reset to the device."""
        ...

    def write(
        self, endpoint: Any, data: Any, timeout: Optional[Any] = None
    ) -> Any:
        """Write *data* to *endpoint*; return the number of bytes written."""
        ...

    def read(
        self, endpoint: Any, size_or_buffer: Any, timeout: Optional[Any] = None
    ) -> Any:
        """Read from *endpoint* into *size_or_buffer*; return bytes read."""
        ...

    def ctrl_transfer(
        self,
        bmRequestType: Any,
        bRequest: Any,
        wValue: int = 0,
        wIndex: int = 0,
        data_or_wLength: Optional[Any] = None,
        timeout: Optional[Any] = None,
    ) -> Any:
        """Perform a USB control transfer and return the response data."""
        ...

    def is_kernel_driver_active(self, interface: Any) -> Any:
        """Return ``True`` if a kernel driver is attached to *interface*."""
        ...

    def detach_kernel_driver(self, interface: Any) -> None:
        """Detach the kernel driver from *interface* so libusb can use it."""
        ...

    def attach_kernel_driver(self, interface: Any) -> None:
        """Re-attach the kernel driver to *interface*."""
        ...

    def __iter__(self) -> Any:
        """Iterate over the configurations of this device."""
        ...

    def __getitem__(self, index: Any) -> Any:
        """Return the configuration at position *index*."""
        ...

@overload
def find(
    find_all: Literal[False] = ...,
    backend: Any = ...,
    custom_match: Optional[Callable[[Device], bool]] = ...,
    **args: Any,
) -> Optional[Device]: ...
@overload
def find(
    find_all: Literal[True],
    backend: Any = ...,
    custom_match: Optional[Callable[[Device], bool]] = ...,
    **args: Any,
) -> List[Device]: ...
def show_devices(verbose: bool = False, **kwargs: Any) -> None:
    """Print a human-readable summary of all attached USB devices."""
    ...
