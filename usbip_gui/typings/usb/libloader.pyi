"""Stub for ``usb.libloader`` — platform-specific shared-library loading."""

__all__ = [
    "LibraryException",
    "LibraryNotFoundException",
    "NoLibraryCandidatesException",
    "LibraryNotLoadedException",
    "LibraryMissingSymbolsException",
    "locate_library",
    "load_library",
    "load_locate_library",
]

class LibraryException(OSError):
    """Base exception raised for any shared-library loading error."""

    ...

class LibraryNotFoundException(LibraryException):
    """Raised when none of the candidate library names could be found."""

    ...

class NoLibraryCandidatesException(LibraryNotFoundException):
    """Raised when the candidate list itself is empty."""

    ...

class LibraryNotLoadedException(LibraryException):
    """Raised when a library was found but could not be loaded."""

    ...

class LibraryMissingSymbolsException(LibraryException):
    """Raised when required symbols are absent from the loaded library."""

    ...

def locate_library(candidates: object, find_library: object = ...) -> object:
    """Search for the first loadable library name in *candidates*."""
    ...

def load_library(
    lib: object,
    name: object = None,
    lib_cls: object = None,
) -> object:
    """
    Load *lib* and return the ctypes handle, optionally wrapped in *lib_cls*.
    """
    ...

def load_locate_library(
    candidates: object,
    cygwin_lib: object,
    name: object,
    win_cls: object = None,
    cygwin_cls: object = None,
    others_cls: object = None,
    find_library: object = None,
    check_symbols: object = None,
) -> object:
    """Locate and load the best candidate library for the current platform."""
    ...
