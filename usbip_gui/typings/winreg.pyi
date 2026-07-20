"""Stub for Windows Registry API for mypy on Linux."""

from typing import Tuple

class HKEYType:
    """Handle to a registry key."""

    def __enter__(self) -> "HKEYType":
        """Enter the context manager, returning the handle."""
        ...

    def __exit__(
        self, exc_type: object, exc_val: object, exc_tb: object
    ) -> None:
        """Exit the context manager, closing the handle."""
        ...

    def Close(self) -> None:
        """Close the underlying Windows handle."""
        ...

HKEY_LOCAL_MACHINE: HKEYType
"""Registry tree for local machine configuration."""

def OpenKey(
    key: HKEYType, sub_key: str, reserved: int = 0, access: int = ...
) -> HKEYType:
    """Open the specified key, returning a handle object."""
    ...

def EnumKey(key: HKEYType, index: int) -> str:
    """Enumerate subkeys of an open registry key, returning a string."""
    ...

def QueryValueEx(key: HKEYType, value_name: str) -> Tuple[object, int]:
    """
    Retrieve the type and data for a specified value name associated with an
    open registry key.
    """
    ...
