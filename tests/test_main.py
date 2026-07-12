"""Tests for the main entry points."""

import runpy
from unittest.mock import MagicMock, patch


@patch("usbip_gui.gui.start_app")
def test_main_module(_mock_start: MagicMock):
    """Test the execution of main.py as a script."""
    with patch("usbip_gui.gui.start_app") as runpy_mock_start:
        runpy.run_module("usbip_gui.main", run_name="__main__")
        runpy_mock_start.assert_called_once()


@patch("usbip_gui.gui.start_app")
def test_dunder_main(_mock_start: MagicMock):
    """Test the execution of __main__.py."""
    with patch("usbip_gui.gui.start_app") as runpy_mock_start:
        runpy.run_module("usbip_gui.__main__", run_name="__main__")
        runpy_mock_start.assert_called_once()
