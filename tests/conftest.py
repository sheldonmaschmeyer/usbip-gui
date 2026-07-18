"""Pytest configuration and fixtures."""

import sys
import pytest
from pytest import MonkeyPatch
from PyQt6.QtWidgets import QApplication

from usbip_gui.common import privilege


@pytest.fixture(scope="session", autouse=True)
def qapp():
    """Create a QApplication instance for all tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture(autouse=True)
def assume_pkexec_available(
    monkeypatch: MonkeyPatch,
) -> None:
    """Make `elevate_command()` deterministically prefer `pkexec` in tests.

    Whether `pkexec` is actually installed varies by host (e.g. it's absent
    in the minimal headless docker test image, which only has `sudo`). Tests
    that assert on the exact elevated command shouldn't depend on that.
    """

    def _which(name: str) -> str | None:
        return "/usr/bin/pkexec" if name == "pkexec" else None

    monkeypatch.setattr(privilege.shutil, "which", _which)
