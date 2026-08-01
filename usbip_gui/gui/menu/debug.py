"""Debug window module for capturing and displaying stdout/stderr."""

import sys
from typing import Optional, TextIO

from PyQt6.QtCore import pyqtSignal, QObject
from PyQt6.QtWidgets import (
    QMainWindow,
    QVBoxLayout,
    QTextEdit,
    QWidget,
    QPushButton,
    QHBoxLayout,
    QApplication,
    QFileDialog,
)
from PyQt6.QtGui import QFont

from usbip_gui.common import get_translator
from usbip_gui.typings import connect_signal

t = get_translator("menu")


class StreamInterceptor(QObject):
    """Intercepts a text stream and emits a signal on write."""

    text_written = pyqtSignal(str)

    def __init__(self, stream: Optional[TextIO]) -> None:
        """Initialize with an existing stream."""
        super().__init__()
        self.stream = stream
        self.history: list[str] = []

    def write(self, text: str) -> None:
        """Write to the original stream and emit the text."""
        if self.stream is not None:
            self.stream.write(text)
        self.history.append(text)
        self.text_written.emit(text)

    def flush(self) -> None:
        """Flush the original stream."""
        if self.stream is not None:
            self.stream.flush()

    def isatty(self) -> bool:
        """Return True if the original stream is a tty."""
        if self.stream is None:
            return False
        return hasattr(self.stream, "isatty") and self.stream.isatty()


class DebugManager:
    """Manages stream interceptors and the debug window instance."""

    stdout_interceptor: Optional[StreamInterceptor] = None
    stderr_interceptor: Optional[StreamInterceptor] = None
    window_instance: Optional["DebugWindow"] = None


def setup_interceptors() -> None:
    """Set up global stream interceptors for stdout and stderr."""
    if DebugManager.stdout_interceptor is None:
        DebugManager.stdout_interceptor = StreamInterceptor(sys.stdout)
        sys.stdout = DebugManager.stdout_interceptor  # type: ignore
    if DebugManager.stderr_interceptor is None:
        DebugManager.stderr_interceptor = StreamInterceptor(sys.stderr)
        sys.stderr = DebugManager.stderr_interceptor  # type: ignore


class DebugWindow(QMainWindow):
    """Window displaying the intercepted stream output."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the debug window."""
        super().__init__(parent)
        self.setWindowTitle(t("Debug Window"))
        self.resize(700, 500)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton(t("Save As..."))
        copy_btn = QPushButton(t("Copy to Clipboard"))
        close_btn = QPushButton(t("Close"))

        connect_signal(save_btn.clicked, self.save_to_file)
        connect_signal(copy_btn.clicked, self.copy_to_clipboard)
        connect_signal(close_btn.clicked, self.close)

        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(copy_btn)
        btn_layout.addWidget(close_btn)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)

        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.text_edit.setFont(QFont("Courier", 10))
        layout.addWidget(self.text_edit)

        if DebugManager.stdout_interceptor is not None:
            self.append_text("".join(DebugManager.stdout_interceptor.history))
            connect_signal(
                DebugManager.stdout_interceptor.text_written, self.append_text
            )
        if DebugManager.stderr_interceptor is not None:
            self.append_text("".join(DebugManager.stderr_interceptor.history))
            connect_signal(
                DebugManager.stderr_interceptor.text_written, self.append_text
            )

    def append_text(self, text: str) -> None:
        """Append text to the read-only text area."""
        cursor = self.text_edit.textCursor()
        self.text_edit.moveCursor(cursor.MoveOperation.End)
        self.text_edit.insertPlainText(text)
        self.text_edit.moveCursor(cursor.MoveOperation.End)

    def save_to_file(self) -> None:
        """Save the current text to a file."""
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            t("Save Debug Output"),
            "",
            t("Text Files (*.txt);;All Files (*)"),
        )
        if file_name:
            with open(file_name, "w", encoding="utf-8") as f:
                f.write(self.text_edit.toPlainText())

    def copy_to_clipboard(self) -> None:
        """Copy the current text to the clipboard."""
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(self.text_edit.toPlainText())


def show_debug_window(parent: Optional[QWidget] = None) -> None:
    """Show the singleton debug window."""
    if DebugManager.window_instance is None:
        DebugManager.window_instance = DebugWindow(parent)
    DebugManager.window_instance.show()
    DebugManager.window_instance.raise_()
    DebugManager.window_instance.activateWindow()
