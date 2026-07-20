"""Top-level ``usb`` package stub — re-exports the legacy PyUSB API."""

from usb.legacy import *  # noqa: F401, F403

__all__ = ["backend", "control", "core", "legacy", "libloader", "util"]
