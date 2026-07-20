"""Stub for ``usb._version`` — PyUSB package version metadata."""

TYPE_CHECKING: bool
"""``True`` only during static type-checking (never at runtime)."""

VERSION_TUPLE = tuple[int | str, ...]
"""Type alias for the structured version tuple."""

version: str
"""PyUSB version string (e.g. ``"1.3.1"``)."""

__version__: str
"""Dunder alias for :data:`version`."""

__version_tuple__: VERSION_TUPLE
"""Structured version tuple (e.g. ``(1, 3, 1)``)."""

version_tuple: VERSION_TUPLE
"""Alias for :data:`__version_tuple__`."""
