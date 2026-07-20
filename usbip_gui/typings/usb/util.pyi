"""Stub for ``usb.util`` — PyUSB utility functions and USB constants."""

from typing import Any, Optional

from usb.core import Device

__all__ = [
    "DESC_TYPE_DEVICE",
    "DESC_TYPE_CONFIG",
    "DESC_TYPE_STRING",
    "DESC_TYPE_INTERFACE",
    "DESC_TYPE_ENDPOINT",
    "ENDPOINT_IN",
    "ENDPOINT_OUT",
    "ENDPOINT_TYPE_CTRL",
    "ENDPOINT_TYPE_ISO",
    "ENDPOINT_TYPE_BULK",
    "ENDPOINT_TYPE_INTR",
    "CTRL_TYPE_STANDARD",
    "CTRL_TYPE_CLASS",
    "CTRL_TYPE_VENDOR",
    "CTRL_TYPE_RESERVED",
    "CTRL_RECIPIENT_DEVICE",
    "CTRL_RECIPIENT_INTERFACE",
    "CTRL_RECIPIENT_ENDPOINT",
    "CTRL_RECIPIENT_OTHER",
    "CTRL_OUT",
    "CTRL_IN",
    "SPEED_LOW",
    "SPEED_FULL",
    "SPEED_HIGH",
    "SPEED_SUPER",
    "SPEED_UNKNOWN",
    "endpoint_address",
    "endpoint_direction",
    "endpoint_type",
    "ctrl_direction",
    "build_request_type",
    "create_buffer",
    "find_descriptor",
    "claim_interface",
    "release_interface",
    "dispose_resources",
    "get_langids",
    "get_string",
]

# ---------------------------------------------------------------------------
# Descriptor type codes
# ---------------------------------------------------------------------------

DESC_TYPE_DEVICE: int
"""Descriptor type: Device (0x01)."""

DESC_TYPE_CONFIG: int
"""Descriptor type: Configuration (0x02)."""

DESC_TYPE_STRING: int
"""Descriptor type: String (0x03)."""

DESC_TYPE_INTERFACE: int
"""Descriptor type: Interface (0x04)."""

DESC_TYPE_ENDPOINT: int
"""Descriptor type: Endpoint (0x05)."""

# ---------------------------------------------------------------------------
# Endpoint direction flags
# ---------------------------------------------------------------------------

ENDPOINT_IN: int
"""Endpoint direction bit: device-to-host (0x80)."""

ENDPOINT_OUT: int
"""Endpoint direction bit: host-to-device (0x00)."""

# ---------------------------------------------------------------------------
# Endpoint transfer-type constants
# ---------------------------------------------------------------------------

ENDPOINT_TYPE_CTRL: int
"""Transfer type: Control."""

ENDPOINT_TYPE_ISO: int
"""Transfer type: Isochronous."""

ENDPOINT_TYPE_BULK: int
"""Transfer type: Bulk."""

ENDPOINT_TYPE_INTR: int
"""Transfer type: Interrupt."""

# ---------------------------------------------------------------------------
# Control-transfer type and recipient constants
# ---------------------------------------------------------------------------

CTRL_TYPE_STANDARD: Any
"""bmRequestType type field: Standard request."""

CTRL_TYPE_CLASS: Any
"""bmRequestType type field: Class-specific request."""

CTRL_TYPE_VENDOR: Any
"""bmRequestType type field: Vendor-specific request."""

CTRL_TYPE_RESERVED: Any
"""bmRequestType type field: Reserved."""

CTRL_RECIPIENT_DEVICE: int
"""bmRequestType recipient: Device."""

CTRL_RECIPIENT_INTERFACE: int
"""bmRequestType recipient: Interface."""

CTRL_RECIPIENT_ENDPOINT: int
"""bmRequestType recipient: Endpoint."""

CTRL_RECIPIENT_OTHER: int
"""bmRequestType recipient: Other."""

CTRL_OUT: int
"""Direction bit: host-to-device (0x00)."""

CTRL_IN: int
"""Direction bit: device-to-host (0x80)."""

# ---------------------------------------------------------------------------
# Speed constants
# ---------------------------------------------------------------------------

SPEED_LOW: int
"""USB low speed (1.5 Mbit/s)."""

SPEED_FULL: int
"""USB full speed (12 Mbit/s)."""

SPEED_HIGH: int
"""USB high speed (480 Mbit/s)."""

SPEED_SUPER: int
"""USB SuperSpeed (5 Gbit/s)."""

SPEED_UNKNOWN: int
"""Speed is not yet determined or not available."""

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def endpoint_address(address: Any) -> Any:
    """Return the endpoint address bits (masking the direction bit)."""
    ...

def endpoint_direction(address: Any) -> Any:
    """Return the direction bit of *address* (:data:`ENDPOINT_IN` or ``OUT``)."""
    ...

def endpoint_type(bmAttributes: Any) -> Any:
    """Return the transfer type encoded in *bmAttributes*."""
    ...

def ctrl_direction(bmRequestType: Any) -> Any:
    """Return the direction bit of *bmRequestType*."""
    ...

def build_request_type(direction: Any, type: Any, recipient: Any) -> Any:
    """Assemble a bmRequestType byte from its three component fields."""
    ...

def create_buffer(length: Any) -> Any:
    """Allocate a ctypes array of *length* bytes suitable for USB transfers."""
    ...

def find_descriptor(
    desc: Any,
    find_all: bool = False,
    custom_match: Optional[Any] = None,
    **args: Any,
) -> Any:
    """Search *desc* for a child descriptor matching *args* criteria."""
    ...

def claim_interface(device: Any, interface: Any) -> None:
    """Claim *interface* on *device* for exclusive use by this process."""
    ...

def release_interface(device: Any, interface: Any) -> None:
    """Release a previously claimed *interface* on *device*."""
    ...

def dispose_resources(device: Any) -> None:
    """Release all resources (interfaces, handles) held for *device*."""
    ...

def get_langids(dev: Any) -> Any:
    """Return the list of language IDs supported by *dev*'s string descriptors."""
    ...

def get_string(
    dev: Device, index: int, langid: Optional[int] = None
) -> Optional[str]:
    """Read and return the USB string descriptor at *index* from *dev*.

    Returns ``None`` if the descriptor is not available.
    """
    ...
