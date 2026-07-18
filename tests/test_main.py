"""Tests for the main entry points."""

import builtins
import runpy
from types import ModuleType
from typing import Mapping, Sequence
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


@patch("usbip_gui.gui.start_app")
def test_dunder_main_fallback_to_absolute_import(_mock_start: MagicMock):
    """Test __main__.py falls back to an absolute import if the relative
    import fails (e.g. when executed directly rather than as a module)."""
    real_import = builtins.__import__

    # pylint: disable=redefined-builtin
    def fake_import(
        name: str,
        globals: Mapping[str, object] | None = None,
        locals: Mapping[str, object] | None = None,
        fromlist: Sequence[str] = (),
        level: int = 0,
    ) -> ModuleType:
        # pylint: enable=redefined-builtin
        if level != 0:
            raise ImportError("simulated relative import failure")
        return real_import(name, globals, locals, fromlist, level)

    with patch("builtins.__import__", side_effect=fake_import):
        with patch("usbip_gui.gui.start_app") as runpy_mock_start:
            runpy.run_module("usbip_gui.__main__", run_name="__main__")
            runpy_mock_start.assert_called_once()
