"""Privilege elevation helpers for Linux and Windows."""

import ctypes
import os
import shutil
import subprocess
import sys
import tempfile
from ctypes import wintypes
from typing import List

_SEE_MASK_NOCLOSEPROCESS = 0x00000040
_SEE_MASK_FLAG_NO_UI = 0x00000400
_SW_HIDE = 0
_ERROR_CANCELLED = 1223
_INFINITE = 0xFFFFFFFF


class _ShellExecuteInfoW(ctypes.Structure):
    """Win32 `SHELLEXECUTEINFOW` structure, used to call `ShellExecuteExW`."""

    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("fMask", ctypes.c_ulong),
        ("hwnd", wintypes.HWND),
        ("lpVerb", wintypes.LPCWSTR),
        ("lpFile", wintypes.LPCWSTR),
        ("lpParameters", wintypes.LPCWSTR),
        ("lpDirectory", wintypes.LPCWSTR),
        ("nShow", ctypes.c_int),
        ("hInstApp", wintypes.HINSTANCE),
        ("lpIDList", ctypes.c_void_p),
        ("lpClass", wintypes.LPCWSTR),
        ("hkeyClass", wintypes.HKEY),
        ("dwHotKey", wintypes.DWORD),
        ("hIcon", wintypes.HANDLE),
        ("hProcess", wintypes.HANDLE),
    ]


def _win_dll(name: str) -> "ctypes.CDLL":
    """Load a Windows DLL by name. Only ever called on `win32`."""
    win_dll = getattr(ctypes, "WinDLL")
    return win_dll(name, use_last_error=True)


def _win_last_error() -> int:
    """Return the last Win32 error code. Only ever called on `win32`."""
    get_last_error = getattr(ctypes, "get_last_error")
    return get_last_error()


def elevate_command(cmd: List[str]) -> List[str]:
    """Prefix a command so it runs with elevated privileges."""
    if shutil.which("pkexec"):
        return ["pkexec"] + cmd
    return ["sudo"] + cmd


def run_elevated_windows(
    cmd: List[str],
) -> "subprocess.CompletedProcess[str]":
    """Run `cmd` elevated on Windows, prompting via a UAC consent dialog."""
    exe = cmd[0]

    fd, temp_path = tempfile.mkstemp(suffix=".log")
    os.close(fd)

    full_cmd = subprocess.list2cmdline(cmd)
    params = f'/c "{full_cmd} > "{temp_path}" 2>&1"'
    working_dir = os.path.dirname(exe) or None

    info = _ShellExecuteInfoW(
        cbSize=ctypes.sizeof(_ShellExecuteInfoW),
        fMask=_SEE_MASK_NOCLOSEPROCESS | _SEE_MASK_FLAG_NO_UI,
        hwnd=None,
        lpVerb="runas",
        lpFile="cmd.exe",
        lpParameters=params,
        lpDirectory=working_dir,
        nShow=_SW_HIDE,
        hInstApp=None,
    )

    shell32 = _win_dll("shell32")
    kernel32 = _win_dll("kernel32")

    if not shell32.ShellExecuteExW(ctypes.pointer(info)):
        error = _win_last_error()
        if error == _ERROR_CANCELLED:
            stderr = "Elevation request was cancelled by the user."
        else:
            stderr = f"Failed to launch elevated process (error {error})."

        try:
            os.remove(temp_path)
        except OSError:
            pass

        return subprocess.CompletedProcess(
            args=cmd, returncode=error or 1, stdout="", stderr=stderr
        )

    kernel32.WaitForSingleObject(info.hProcess, _INFINITE)
    exit_code = wintypes.DWORD()
    kernel32.GetExitCodeProcess(info.hProcess, ctypes.pointer(exit_code))
    kernel32.CloseHandle(info.hProcess)

    stdout_content = ""
    try:
        with open(temp_path, "r", encoding="utf-8", errors="replace") as f:
            stdout_content = f.read()
        os.remove(temp_path)
    except OSError:
        pass

    stderr = ""
    if exit_code.value != 0:
        stderr = (
            "Elevated process exited with error code " f"{exit_code.value}.\n"
        )

    if stdout_content:
        stderr += stdout_content

    return subprocess.CompletedProcess(
        args=cmd,
        returncode=exit_code.value,
        stdout=stdout_content,
        stderr=stderr,
    )


def run_elevated(cmd: List[str]) -> "subprocess.CompletedProcess[str]":
    """Run a command that requires administrator/root privileges."""
    if sys.platform == "win32":
        return run_elevated_windows(cmd)
    return subprocess.run(
        elevate_command(cmd), capture_output=True, text=True, check=False
    )
