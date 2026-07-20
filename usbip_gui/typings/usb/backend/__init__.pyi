"""Stub for ``usb.backend`` — abstract backend interface for USB I/O.

Concrete implementations live in :mod:`usb.backend.libusb0` and
:mod:`usb.backend.libusb1`.
"""

import usb._objfinalizer as _objfinalizer

__all__ = ["IBackend", "libusb0", "libusb1", "openusb"]

class IBackend(_objfinalizer.AutoFinalizedObject):
    """Abstract interface that every USB backend must implement.

    Subclasses wrap a specific native library (libusb 0.x, libusb 1.x, or
    OpenUSB) and translate its API into the methods below.
    """

    def enumerate_devices(self) -> None:
        """Yield all USB devices currently visible to the backend."""
        ...

    def get_parent(self, dev: object) -> None:
        """Return the parent hub device of *dev*, or ``None``."""
        ...

    def get_device_descriptor(self, dev: object) -> None:
        """Return the device descriptor for *dev*."""
        ...

    def get_configuration_descriptor(
        self, dev: object, config: object
    ) -> None:
        """Return the configuration descriptor at index *config* for *dev*."""
        ...

    def get_interface_descriptor(
        self, dev: object, intf: object, alt: object, config: object
    ) -> None:
        """Return the interface descriptor for *intf*/*alt* in *config*."""
        ...

    def get_endpoint_descriptor(
        self,
        dev: object,
        ep: object,
        intf: object,
        alt: object,
        config: object,
    ) -> None:
        """Return the endpoint descriptor for *ep* in *intf*/*alt*/*config*."""
        ...

    def open_device(self, dev: object) -> None:
        """Open *dev* and return a device handle."""
        ...

    def close_device(self, dev_handle: object) -> None:
        """Close *dev_handle* and release the associated OS resources."""
        ...

    def set_configuration(
        self, dev_handle: object, config_value: object
    ) -> None:
        """Activate the configuration numbered *config_value* on *dev_handle*."""
        ...

    def get_configuration(self, dev_handle: object) -> None:
        """Return the currently active configuration value for *dev_handle*."""
        ...

    def set_interface_altsetting(
        self, dev_handle: object, intf: object, altsetting: object
    ) -> None:
        """Switch *intf* on *dev_handle* to alternate setting *altsetting*."""
        ...

    def claim_interface(self, dev_handle: object, intf: object) -> None:
        """Claim *intf* on *dev_handle* for exclusive use."""
        ...

    def release_interface(self, dev_handle: object, intf: object) -> None:
        """Release a previously claimed *intf* on *dev_handle*."""
        ...

    def bulk_write(
        self,
        dev_handle: object,
        ep: object,
        intf: object,
        data: object,
        timeout: object,
    ) -> None:
        """Write *data* to bulk endpoint *ep* on *dev_handle*."""
        ...

    def bulk_read(
        self,
        dev_handle: object,
        ep: object,
        intf: object,
        buff: object,
        timeout: object,
    ) -> None:
        """Read from bulk endpoint *ep* on *dev_handle* into *buff*."""
        ...

    def intr_write(
        self,
        dev_handle: object,
        ep: object,
        intf: object,
        data: object,
        timeout: object,
    ) -> None:
        """Write *data* to interrupt endpoint *ep* on *dev_handle*."""
        ...

    def intr_read(
        self,
        dev_handle: object,
        ep: object,
        intf: object,
        size: object,
        timeout: object,
    ) -> None:
        """Read from interrupt endpoint *ep* on *dev_handle*."""
        ...

    def iso_write(
        self,
        dev_handle: object,
        ep: object,
        intf: object,
        data: object,
        timeout: object,
    ) -> None:
        """Write *data* to isochronous endpoint *ep* on *dev_handle*."""
        ...

    def iso_read(
        self,
        dev_handle: object,
        ep: object,
        intf: object,
        size: object,
        timeout: object,
    ) -> None:
        """Read from isochronous endpoint *ep* on *dev_handle*."""
        ...

    def ctrl_transfer(
        self,
        dev_handle: object,
        bmRequestType: object,
        bRequest: object,
        wValue: object,
        wIndex: object,
        data: object,
        timeout: object,
    ) -> None:
        """Perform a control transfer on *dev_handle*."""
        ...

    def clear_halt(self, dev_handle: object, ep: object) -> None:
        """Clear the halt/stall condition on endpoint *ep*."""
        ...

    def reset_device(self, dev_handle: object) -> None:
        """Issue a USB reset to the device behind *dev_handle*."""
        ...

    def is_kernel_driver_active(
        self, dev_handle: object, intf: object
    ) -> None:
        """Return ``True`` if a kernel driver is attached to *intf*."""
        ...

    def detach_kernel_driver(self, dev_handle: object, intf: object) -> None:
        """Detach the kernel driver from *intf* so libusb can claim it."""
        ...

    def attach_kernel_driver(self, dev_handle: object, intf: object) -> None:
        """Re-attach the kernel driver to *intf*."""
        ...
