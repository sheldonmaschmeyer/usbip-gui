"""
Type hints and wrappers for the usbip-gui.

This module provides strongly-typed wrappers for PyQt6 methods whose type stubs
are either incomplete, use `Unknown`, or lack specificity. By using these
wrappers, we avoid suppressing strict type-checker rules (like
`reportUnknownMemberType`) throughout the codebase.

Linter exceptions used in this file:

- `# pragma: no cover`: Used on `raise NotImplementedError` lines inside
  Protocols. Because Protocols are purely for static type definition, their
  bodies are never executed at runtime. This pragma ensures they don't
  incorrectly drop test coverage.

- `# pylint: disable=invalid-name`: Used on Protocol methods like
  `setHeaderLabels` and `addAction`. PyQt strictly inherits C++ camelCase
  conventions, which conflict with Python's standard PEP-8 snake_case. We must
  disable the linter here because the Protocol method name MUST exactly match
  the underlying Qt C++ method name.
"""

from typing import Callable, cast, Protocol, TypeVar, ParamSpec, Iterable
from PyQt6.QtCore import pyqtBoundSignal, QMetaObject
from PyQt6.QtWidgets import QTreeWidget
from PyQt6.QtGui import QAction

P = ParamSpec("P")
R = TypeVar("R")


class _TypedSignal(Protocol):
    """Protocol for strongly typing the connect method of pyqtBoundSignal."""

    def connect(self, slot: Callable[P, R], /) -> QMetaObject.Connection:
        """Connect a slot to the signal."""
        raise NotImplementedError  # pragma: no cover


def connect_signal(
    signal: pyqtBoundSignal, slot: Callable[P, R]
) -> QMetaObject.Connection:
    """
    Strongly typed signal connection wrapper to satisfy Pyright
    without losing type safety.
    """
    return cast(_TypedSignal, signal).connect(slot)


class _TreeWidgetHeaderLabels(Protocol):
    """Protocol for strongly typing the setHeaderLabels method."""

    # pylint: disable=invalid-name
    def setHeaderLabels(self, labels: Iterable[str]) -> None:
        """Set header labels."""
        raise NotImplementedError  # pragma: no cover


def set_header_labels(tree: QTreeWidget, labels: Iterable[str]) -> None:
    """
    Strongly typed wrapper for QTreeWidget.setHeaderLabels to satisfy Pyright.
    """
    cast(_TreeWidgetHeaderLabels, tree).setHeaderLabels(labels)


class _AddAction(Protocol):
    """Protocol for strongly typing the addAction method."""

    # pylint: disable=invalid-name
    def addAction(self, action: QAction) -> None:
        """Add action."""
        raise NotImplementedError  # pragma: no cover


def add_action(parent: object, action: QAction) -> None:
    """
    Strongly typed wrapper for addAction to satisfy Pyright.
    """
    cast(_AddAction, parent).addAction(action)
