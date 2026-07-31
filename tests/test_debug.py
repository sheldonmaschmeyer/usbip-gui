"""Tests for the debug menu components."""

import sys
from unittest.mock import MagicMock, patch, mock_open

import pytest

from usbip_gui.gui.menu.debug import (
    StreamInterceptor,
    DebugManager,
    setup_interceptors,
    DebugWindow,
    show_debug_window,
)
from usbip_gui.typings import connect_signal


@pytest.fixture(autouse=True)
def reset_debug_manager():
    """Reset the DebugManager singleton state before each test."""
    DebugManager.stdout_interceptor = None
    DebugManager.stderr_interceptor = None
    DebugManager.window_instance = None
    yield
    DebugManager.stdout_interceptor = None
    DebugManager.stderr_interceptor = None
    DebugManager.window_instance = None


def test_stream_interceptor_write_and_flush():
    """Test StreamInterceptor writes to stream and emits signal."""
    mock_stream = MagicMock()
    interceptor = StreamInterceptor(mock_stream)

    # Test flush
    interceptor.flush()
    mock_stream.flush.assert_called_once()

    # Test write
    mock_slot = MagicMock()
    connect_signal(interceptor.text_written, mock_slot)

    interceptor.write("test data")
    mock_stream.write.assert_called_once_with("test data")
    assert interceptor.history == ["test data"]
    mock_slot.assert_called_once_with("test data")


def test_stream_interceptor_none_stream():
    """Test StreamInterceptor works safely when stream is None."""
    interceptor = StreamInterceptor(None)

    interceptor.flush()  # Should not raise

    mock_slot = MagicMock()
    connect_signal(interceptor.text_written, mock_slot)
    interceptor.write("test data")
    assert interceptor.history == ["test data"]
    mock_slot.assert_called_once_with("test data")

    assert interceptor.isatty() is False


def test_stream_interceptor_isatty():
    """Test StreamInterceptor correctly proxies isatty()."""
    # Stream with isatty returning True
    mock_stream1 = MagicMock()
    mock_stream1.isatty.return_value = True
    assert StreamInterceptor(mock_stream1).isatty() is True

    # Stream without isatty
    class DummyStream:
        """A dummy stream without isatty."""

    from typing import cast, TextIO

    assert StreamInterceptor(cast(TextIO, DummyStream())).isatty() is False


def test_setup_interceptors():
    """
    Test setup_interceptors creates interceptors on
    sys.stdout and sys.stderr.
    """
    original_stdout = sys.stdout
    original_stderr = sys.stderr

    try:
        setup_interceptors()
        assert DebugManager.stdout_interceptor is not None
        assert DebugManager.stderr_interceptor is not None
        assert sys.stdout is DebugManager.stdout_interceptor
        assert sys.stderr is DebugManager.stderr_interceptor

        # Test idempotency (should not overwrite if already set)
        first_stdout = DebugManager.stdout_interceptor
        setup_interceptors()
        assert DebugManager.stdout_interceptor is first_stdout
    finally:
        sys.stdout = original_stdout
        sys.stderr = original_stderr


def test_debug_window_init():
    """Test DebugWindow initializes correctly and loads history."""
    with patch("usbip_gui.gui.menu.debug.QMainWindow.setCentralWidget"), patch(
        "usbip_gui.gui.menu.debug.QMainWindow.setWindowTitle"
    ), patch("usbip_gui.gui.menu.debug.QMainWindow.resize"), patch(
        "usbip_gui.gui.menu.debug.QWidget"
    ), patch(
        "usbip_gui.gui.menu.debug.QVBoxLayout"
    ), patch(
        "usbip_gui.gui.menu.debug.QHBoxLayout"
    ), patch(
        "usbip_gui.gui.menu.debug.QPushButton"
    ), patch(
        "usbip_gui.gui.menu.debug.QTextEdit"
    ):

        # Setup some history
        setup_interceptors()
        assert DebugManager.stdout_interceptor is not None
        assert DebugManager.stderr_interceptor is not None
        DebugManager.stdout_interceptor.history = ["out1", "out2"]
        DebugManager.stderr_interceptor.history = ["err1"]

        window = DebugWindow()
        assert window is not None


def test_debug_window_init_no_interceptors():
    """Test DebugWindow initializes when interceptors are None."""
    with patch("usbip_gui.gui.menu.debug.QMainWindow.setCentralWidget"), patch(
        "usbip_gui.gui.menu.debug.QMainWindow.setWindowTitle"
    ), patch("usbip_gui.gui.menu.debug.QMainWindow.resize"), patch(
        "usbip_gui.gui.menu.debug.QWidget"
    ), patch(
        "usbip_gui.gui.menu.debug.QVBoxLayout"
    ), patch(
        "usbip_gui.gui.menu.debug.QHBoxLayout"
    ), patch(
        "usbip_gui.gui.menu.debug.QPushButton"
    ), patch(
        "usbip_gui.gui.menu.debug.QTextEdit"
    ):

        DebugManager.stdout_interceptor = None
        DebugManager.stderr_interceptor = None
        window = DebugWindow()
        assert window is not None


def test_debug_window_append_text():
    """Test DebugWindow.append_text manipulates cursor properly."""
    # Using real Qt objects is harder in unit tests without a QApplication,
    # so we mock the QTextEdit and its cursor.
    window = MagicMock(spec=DebugWindow)
    window.text_edit = MagicMock()
    mock_cursor = MagicMock()
    window.text_edit.textCursor.return_value = mock_cursor

    DebugWindow.append_text(window, "new log")

    window.text_edit.textCursor.assert_called_once()
    assert window.text_edit.moveCursor.call_count == 2
    window.text_edit.insertPlainText.assert_called_once_with("new log")


@patch("usbip_gui.gui.menu.debug.QFileDialog")
@patch("builtins.open", new_callable=mock_open)
def test_debug_window_save_to_file(
    mock_file: MagicMock, mock_qfiledialog: MagicMock
):
    """Test DebugWindow.save_to_file writes text to file."""
    window = MagicMock(spec=DebugWindow)
    window.text_edit = MagicMock()
    window.text_edit.toPlainText.return_value = "full logs"

    # Simulate user picking a file
    mock_qfiledialog.getSaveFileName.return_value = (
        "test.log",
        "Text Files (*.txt)",
    )

    DebugWindow.save_to_file(window)

    mock_file.assert_called_once_with("test.log", "w", encoding="utf-8")
    mock_file().write.assert_called_once_with("full logs")


@patch("usbip_gui.gui.menu.debug.QFileDialog")
@patch("builtins.open", new_callable=mock_open)
def test_debug_window_save_to_file_cancelled(
    mock_file: MagicMock, mock_qfiledialog: MagicMock
):
    """Test DebugWindow.save_to_file does nothing if dialog cancelled."""
    window = MagicMock(spec=DebugWindow)

    # Simulate user cancelling dialog
    mock_qfiledialog.getSaveFileName.return_value = ("", "")

    DebugWindow.save_to_file(window)
    mock_file.assert_not_called()


@patch("usbip_gui.gui.menu.debug.QApplication")
def test_debug_window_copy_to_clipboard(mock_qapp: MagicMock):
    """Test DebugWindow.copy_to_clipboard uses QApplication clipboard."""
    window = MagicMock(spec=DebugWindow)
    window.text_edit = MagicMock()
    window.text_edit.toPlainText.return_value = "full logs"

    mock_clipboard = MagicMock()
    mock_qapp.clipboard.return_value = mock_clipboard

    DebugWindow.copy_to_clipboard(window)

    mock_clipboard.setText.assert_called_once_with("full logs")


@patch("usbip_gui.gui.menu.debug.QApplication")
def test_debug_window_copy_to_clipboard_none(mock_qapp: MagicMock):
    """Test copy_to_clipboard when clipboard is None."""
    window = MagicMock(spec=DebugWindow)
    mock_qapp.clipboard.return_value = None
    DebugWindow.copy_to_clipboard(window)  # Should not raise


@patch("usbip_gui.gui.menu.debug.DebugWindow")
def test_show_debug_window(mock_debug_window_class: MagicMock):
    """Test show_debug_window creates singleton and shows it."""
    mock_instance = MagicMock()
    mock_debug_window_class.return_value = mock_instance

    show_debug_window(None)

    mock_debug_window_class.assert_called_once_with(None)
    mock_instance.show.assert_called_once()
    mock_instance.raise_.assert_called_once()
    mock_instance.activateWindow.assert_called_once()

    # Second call should reuse singleton
    show_debug_window(None)
    assert mock_debug_window_class.call_count == 1
    assert mock_instance.show.call_count == 2
