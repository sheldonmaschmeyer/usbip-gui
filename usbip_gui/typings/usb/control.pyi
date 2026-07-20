"""Stub for ``usb.control`` — standard USB control-transfer helpers."""

from typing import Any, Optional

import usb.core as core

__all__ = [
    "get_status",
    "clear_feature",
    "set_feature",
    "get_descriptor",
    "set_descriptor",
    "get_configuration",
    "set_configuration",
    "get_interface",
    "set_interface",
    "ENDPOINT_HALT",
    "FUNCTION_SUSPEND",
    "DEVICE_REMOTE_WAKEUP",
    "U1_ENABLE",
    "U2_ENABLE",
    "LTM_ENABLE",
]

USBError = core.USBError
"""Re-export of :class:`usb.core.USBError` for convenience."""

ENDPOINT_HALT: int
"""Feature selector for halting an endpoint (USB spec §9.4)."""

FUNCTION_SUSPEND: int
"""Feature selector for function suspend (USB 3.x §9.4.9)."""

DEVICE_REMOTE_WAKEUP: int
"""Feature selector for remote wakeup capability."""

U1_ENABLE: int
"""Feature selector to enable U1 low-power state (SuperSpeed)."""

U2_ENABLE: int
"""Feature selector to enable U2 low-power state (SuperSpeed)."""

LTM_ENABLE: int
"""Feature selector for Latency Tolerance Messaging."""

def get_status(dev: Any, recipient: Optional[Any] = None) -> Any:
    """Return the status word for *dev* (or a specific *recipient*)."""
    ...

def clear_feature(
    dev: Any, feature: Any, recipient: Optional[Any] = None
) -> None:
    """Send a ClearFeature request to *dev* for *feature*."""
    ...

def set_feature(
    dev: Any, feature: Any, recipient: Optional[Any] = None
) -> None:
    """Send a SetFeature request to *dev* for *feature*."""
    ...

def get_descriptor(
    dev: Any,
    desc_size: Any,
    desc_type: Any,
    desc_index: Any,
    wIndex: int = 0,
) -> Any:
    """Fetch a USB descriptor of *desc_type* and *desc_index* from *dev*."""
    ...

def set_descriptor(
    dev: Any,
    desc: Any,
    desc_type: Any,
    desc_index: Any,
    wIndex: Optional[Any] = None,
) -> None:
    """Write *desc* to *dev* as a descriptor of *desc_type*/*desc_index*."""
    ...

def get_configuration(dev: Any) -> Any:
    """Return the current configuration value of *dev*."""
    ...

def set_configuration(dev: Any, bConfigurationNumber: Any) -> None:
    """Activate configuration *bConfigurationNumber* on *dev*."""
    ...

def get_interface(dev: Any, bInterfaceNumber: Any) -> Any:
    """Return the active alternate setting for *bInterfaceNumber* on *dev*."""
    ...

def set_interface(
    dev: Any, bInterfaceNumber: Any, bAlternateSetting: Any
) -> None:
    """Select alternate setting *bAlternateSetting* for *bInterfaceNumber*."""
    ...
