"""Stub for ``usb._debug`` — trace-logging decorators."""

from typing import Any, Callable, TypeVar

_F = TypeVar("_F", bound=Callable[..., Any])

__all__ = ["methodtrace", "functiontrace"]

def methodtrace(logger: Any) -> Callable[[_F], _F]:
    """Decorate a method to emit entry/exit trace logs via *logger*."""
    ...

def functiontrace(logger: Any) -> Callable[[_F], _F]:
    """Decorate a function to emit entry/exit trace logs via *logger*."""
    ...
