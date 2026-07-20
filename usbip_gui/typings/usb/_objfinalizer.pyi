"""
Stub for ``usb._objfinalizer`` — deterministic resource-cleanup base classes.
"""

__all__ = ["AutoFinalizedObject"]

class _AutoFinalizedObjectBase:
    """Internal base that wires ``__del__`` to a user-overridable finalizer."""

    def finalize(self) -> None:
        """Release all resources held by this object."""
        ...

    def __del__(self) -> None:
        """Call :meth:`finalize` when the object is garbage-collected."""
        ...

class AutoFinalizedObject(_AutoFinalizedObjectBase):
    """Public base class; subclasses override :meth:`finalize` for cleanup."""

    def finalize(self) -> None:
        """Override to release device handles or other OS resources."""
        ...
