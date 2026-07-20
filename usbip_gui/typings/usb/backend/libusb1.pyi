"""Stub for ``usb.backend.libusb1`` — libusb 1.x backend for PyUSB."""

from ctypes import Structure
from typing import Any

import usb._objfinalizer as _objfinalizer

__all__ = [
    "get_backend",
    "LIBUSB_SUCCESS",
    "LIBUSB_ERROR_IO",
    "LIBUSB_ERROR_INVALID_PARAM",
    "LIBUSB_ERROR_ACCESS",
    "LIBUSB_ERROR_NO_DEVICE",
    "LIBUSB_ERROR_NOT_FOUND",
    "LIBUSB_ERROR_BUSY",
    "LIBUSB_ERROR_TIMEOUT",
    "LIBUSB_ERROR_OVERFLOW",
    "LIBUSB_ERROR_PIPE",
    "LIBUSB_ERROR_INTERRUPTED",
    "LIBUSB_ERROR_NO_MEM",
    "LIBUSB_ERROR_NOT_SUPPORTED",
    "LIBUSB_ERROR_OTHER",
    "LIBUSB_TRANSFER_COMPLETED",
    "LIBUSB_TRANSFER_ERROR",
    "LIBUSB_TRANSFER_TIMED_OUT",
    "LIBUSB_TRANSFER_CANCELLED",
    "LIBUSB_TRANSFER_STALL",
    "LIBUSB_TRANSFER_NO_DEVICE",
    "LIBUSB_TRANSFER_OVERFLOW",
]

# ---------------------------------------------------------------------------
# libusb 1.x return / status codes
# ---------------------------------------------------------------------------

LIBUSB_SUCCESS: int
"""Operation completed successfully."""

LIBUSB_ERROR_IO: int
"""Input/output error."""

LIBUSB_ERROR_INVALID_PARAM: int
"""Invalid parameter passed to libusb."""

LIBUSB_ERROR_ACCESS: int
"""Access denied (insufficient permissions)."""

LIBUSB_ERROR_NO_DEVICE: int
"""No such device (it may have been disconnected)."""

LIBUSB_ERROR_NOT_FOUND: int
"""Entity not found."""

LIBUSB_ERROR_BUSY: int
"""Resource busy."""

LIBUSB_ERROR_TIMEOUT: int
"""Operation timed out."""

LIBUSB_ERROR_OVERFLOW: int
"""Overflow — device sent more data than expected."""

LIBUSB_ERROR_PIPE: int
"""Pipe error (endpoint halted)."""

LIBUSB_ERROR_INTERRUPTED: int
"""System call interrupted (possibly due to signal)."""

LIBUSB_ERROR_NO_MEM: int
"""Insufficient memory."""

LIBUSB_ERROR_NOT_SUPPORTED: int
"""Operation not supported or unimplemented."""

LIBUSB_ERROR_OTHER: int
"""Other / unspecified error."""

LIBUSB_TRANSFER_COMPLETED: int
"""Transfer completed without error."""

LIBUSB_TRANSFER_ERROR: int
"""Transfer failed."""

LIBUSB_TRANSFER_TIMED_OUT: int
"""Transfer timed out."""

LIBUSB_TRANSFER_CANCELLED: int
"""Transfer was cancelled."""

LIBUSB_TRANSFER_STALL: int
"""For bulk/interrupt endpoints: halt condition detected."""

LIBUSB_TRANSFER_NO_DEVICE: int
"""Device was disconnected."""

LIBUSB_TRANSFER_OVERFLOW: int
"""Device sent more data than requested."""

# ---------------------------------------------------------------------------
# Low-level ctypes structure stubs (intentionally opaque)
# ---------------------------------------------------------------------------

class _libusb_endpoint_descriptor(Structure):
    """Raw libusb 1.x endpoint descriptor."""

    ...

class _libusb_interface_descriptor(Structure):
    """Raw libusb 1.x interface descriptor."""

    ...

class _libusb_interface(Structure):
    """Raw libusb 1.x interface (collection of alternate settings)."""

    ...

class _libusb_config_descriptor(Structure):
    """Raw libusb 1.x configuration descriptor."""

    ...

class _libusb_device_descriptor(Structure):
    """Raw libusb 1.x device descriptor."""

    ...

class _libusb_iso_packet_descriptor(Structure):
    """Raw descriptor for one isochronous packet in a transfer."""

    ...

class _libusb_transfer(Structure):
    """Raw libusb 1.x asynchronous transfer structure."""

    ...

class _Device(_objfinalizer.AutoFinalizedObject):
    """Opaque wrapper around a ``libusb_device *`` pointer."""

    devid: Any
    """Internal identifier used to track the underlying libusb device."""

    def __init__(self, devid: Any) -> None:
        """Wrap the libusb device pointer *devid*."""
        ...

class _WrapDescriptor:
    """Thin wrapper that exposes a libusb descriptor as Python attributes."""

    obj: Any
    """Underlying libusb object (device or config descriptor)."""

    desc: Any
    """The raw ctypes descriptor structure being wrapped."""

    def __init__(self, desc: Any, obj: Any = None) -> None:
        """Wrap *desc*, optionally keeping a reference to its parent *obj*."""
        ...

    def __getattr__(self, name: str) -> Any:
        """Proxy attribute access to the underlying descriptor struct."""
        ...

class _ConfigDescriptor(_objfinalizer.AutoFinalizedObject):
    """Auto-finalised wrapper around a libusb 1.x configuration descriptor."""

    desc: Any
    """The raw ``libusb_config_descriptor *`` pointer."""

    def __init__(self, desc: Any) -> None:
        """Wrap *desc* and register it for automatic freeing."""
        ...

    def __getattr__(self, name: str) -> Any:
        """Proxy attribute access to the underlying descriptor struct."""
        ...

def get_backend(find_library: Any = None) -> Any:
    """Return a libusb 1.x backend instance, or ``None`` if libusb is absent."""
    ...
