"""Tests for the common gui components."""

import json
import os
from ctypes import wintypes
from pathlib import Path
from typing import Callable
from unittest.mock import patch, MagicMock
from PyQt6.QtWidgets import QTreeWidget
from usbip_gui.common import (
    TunnelState,
    cleanup_tunnels,
    tunnel_state,
    get_translator,
    get_config_dir,
    load_config,
    save_config,
    SortableTreeWidgetItem,
    set_min_column_widths,
    _detect_system_language,  # pyright: ignore[reportPrivateUsage]
    get_current_language,
    set_language,
    language_changed,
    elevate_command,
    run_elevated,
)
import usbip_gui.common.privilege as privilege_mod


def test_tunnel_state_initialization():
    """Test that TunnelState initializes with empty/None processes."""
    state = TunnelState()
    assert state.server_process is None
    assert not state.client_processes


@patch("usbip_gui.common.privilege.ctypes.WinDLL", create=True)
def test_win_dll_wrapper(mock_windll: MagicMock):
    """Test _win_dll delegates to ctypes.WinDLL with last-error enabled."""
    sentinel = MagicMock()
    mock_windll.return_value = sentinel
    win_dll = getattr(privilege_mod, "_win_dll")
    assert win_dll("shell32") is sentinel
    mock_windll.assert_called_once_with("shell32", use_last_error=True)


@patch(
    "usbip_gui.common.privilege.ctypes.get_last_error",
    return_value=5,
    create=True,
)
def test_win_last_error_wrapper(mock_get_last_error: MagicMock):
    """Test _win_last_error delegates to ctypes.get_last_error."""
    win_last_error = getattr(privilege_mod, "_win_last_error")
    assert win_last_error() == 5
    mock_get_last_error.assert_called_once()


def test_elevate_command_prefers_pkexec():
    """Test elevate_command uses pkexec when it's available."""
    with patch(
        "usbip_gui.common.privilege.shutil.which",
        return_value="/usr/bin/pkexec",
    ):
        assert elevate_command(["usbip", "port"]) == [
            "pkexec",
            "usbip",
            "port",
        ]


def test_elevate_command_falls_back_to_sudo():
    """Test elevate_command falls back to sudo when pkexec is missing."""
    with patch("usbip_gui.common.privilege.shutil.which", return_value=None):
        assert elevate_command(["usbip", "port"]) == [
            "sudo",
            "usbip",
            "port",
        ]


@patch("usbip_gui.common.privilege.subprocess.run")
def test_run_elevated_linux(mock_run: MagicMock):
    """Test run_elevated uses elevate_command + subprocess.run on Linux."""
    with patch("usbip_gui.common.privilege.sys.platform", "linux"):
        with patch(
            "usbip_gui.common.privilege.shutil.which",
            return_value="/usr/bin/pkexec",
        ):
            run_elevated(["usbip", "port"])

    mock_run.assert_called_once_with(
        ["pkexec", "usbip", "port"],
        capture_output=True,
        text=True,
        check=False,
    )


def _fake_win_dll(
    shell32: MagicMock, kernel32: MagicMock
) -> Callable[[str], MagicMock]:
    """Build a `_win_dll` side_effect returning fixed per-name mocks."""
    dlls = {"shell32": shell32, "kernel32": kernel32}

    def _win_dll(name: str) -> MagicMock:
        return dlls[name]

    return _win_dll


def _fake_get_exit_code(_handle: int, ptr: wintypes.LPDWORD) -> int:
    """Fake `GetExitCodeProcess`, writing a success code through `ptr`."""
    ptr.contents.value = 0
    return 1


def _fake_get_exit_code_106(_handle: int, ptr: wintypes.LPDWORD) -> int:
    """Fake `GetExitCodeProcess`, writing a nonzero error code."""
    ptr.contents.value = 106
    return 1


@patch("usbip_gui.common.privilege._win_dll")
def test_run_elevated_windows(mock_win_dll: MagicMock):
    """Test run_elevated calls ShellExecuteExW with the "runas" verb."""
    mock_shell32 = MagicMock()
    mock_kernel32 = MagicMock()
    mock_win_dll.side_effect = _fake_win_dll(mock_shell32, mock_kernel32)
    mock_shell32.ShellExecuteExW.return_value = 1
    mock_kernel32.GetExitCodeProcess.side_effect = _fake_get_exit_code

    with patch("usbip_gui.common.privilege.sys.platform", "win32"):
        result = run_elevated(["usbipd", "bind", "--busid", "1-1"])

    info = mock_shell32.ShellExecuteExW.call_args[0][0].contents
    assert info.lpVerb == "runas"
    assert info.lpFile == "usbipd"
    assert info.lpParameters == "bind --busid 1-1"
    mock_kernel32.WaitForSingleObject.assert_called_once()
    mock_kernel32.CloseHandle.assert_called_once()
    assert result.returncode == 0


@patch("usbip_gui.common.privilege._win_last_error")
@patch("usbip_gui.common.privilege._win_dll")
def test_run_elevated_windows_cancelled(
    mock_win_dll: MagicMock, mock_last_error: MagicMock
):
    """Test run_elevated surfaces a clear error if UAC is cancelled."""
    mock_shell32 = MagicMock()
    mock_kernel32 = MagicMock()
    mock_win_dll.side_effect = _fake_win_dll(mock_shell32, mock_kernel32)
    mock_shell32.ShellExecuteExW.return_value = 0
    mock_last_error.return_value = 1223

    with patch("usbip_gui.common.privilege.sys.platform", "win32"):
        result = run_elevated(["usbipd", "bind", "--busid", "1-1"])

    assert result.returncode == 1223
    assert "cancelled" in result.stderr.lower()
    mock_kernel32.WaitForSingleObject.assert_not_called()


@patch("usbip_gui.common.privilege._win_last_error")
@patch("usbip_gui.common.privilege._win_dll")
def test_run_elevated_windows_reports_real_error(
    mock_win_dll: MagicMock, mock_last_error: MagicMock
):
    """Test a genuine ShellExecuteExW failure isn't masked as "cancelled"."""
    mock_shell32 = MagicMock()
    mock_kernel32 = MagicMock()
    mock_win_dll.side_effect = _fake_win_dll(mock_shell32, mock_kernel32)
    mock_shell32.ShellExecuteExW.return_value = 0
    mock_last_error.return_value = 2  # ERROR_FILE_NOT_FOUND

    with patch("usbip_gui.common.privilege.sys.platform", "win32"):
        result = run_elevated(["usbipd", "bind", "--busid", "1-1"])

    assert result.returncode == 2
    assert "2" in result.stderr
    assert "cancelled" not in result.stderr.lower()


@patch("usbip_gui.common.privilege._win_dll")
def test_run_elevated_windows_nonzero_exit_code_message(
    mock_win_dll: MagicMock,
):
    """Test nonzero elevated process exit code returns neutral stderr."""
    mock_shell32 = MagicMock()
    mock_kernel32 = MagicMock()
    mock_win_dll.side_effect = _fake_win_dll(mock_shell32, mock_kernel32)
    mock_shell32.ShellExecuteExW.return_value = 1
    mock_kernel32.GetExitCodeProcess.side_effect = _fake_get_exit_code_106

    with patch("usbip_gui.common.privilege.sys.platform", "win32"):
        result = run_elevated(["usbip", "attach", "--busid=2-2"])

    assert result.returncode == 106
    assert "elevated process exited" in result.stderr.lower()
    assert "106" in result.stderr


def test_cleanup_tunnels_no_processes():
    """
    Test that cleanup_tunnels runs without error when no processes exist.
    """
    cleanup_tunnels()
    assert tunnel_state.server_process is None


def test_cleanup_tunnels_with_processes():
    """Test cleanup_tunnels with active processes."""
    server_proc = MagicMock()
    client_proc = MagicMock()
    tunnel_state.server_process = server_proc
    tunnel_state.client_processes = {("host", 123): (123, client_proc, "pwd")}

    cleanup_tunnels()
    server_proc.terminate.assert_called_once()
    client_proc.terminate.assert_called_once()
    tunnel_state.server_process = None
    tunnel_state.client_processes.clear()


def test_cleanup_tunnels_with_oserror():
    """Test cleanup_tunnels handles OSError gracefully."""
    server_proc = MagicMock()
    server_proc.terminate.side_effect = OSError()
    client_proc = MagicMock()
    client_proc.terminate.side_effect = OSError()

    tunnel_state.server_process = server_proc
    tunnel_state.client_processes = {("host", 123): (123, client_proc, "pwd")}

    cleanup_tunnels()
    server_proc.terminate.assert_called_once()
    client_proc.terminate.assert_called_once()
    tunnel_state.server_process = None
    tunnel_state.client_processes.clear()


@patch("usbip_gui.common.languages.Path.exists")
@patch("builtins.open")
@patch("usbip_gui.common.languages.json.load")
def test_get_translator_common(
    mock_json_load: MagicMock, _mock_open: MagicMock, mock_exists: MagicMock
):
    """Test get_translator for common domain."""
    mock_exists.return_value = True
    mock_json_load.return_value = {"hello": "bonjour"}

    t_func = get_translator("common")
    assert callable(t_func)
    assert t_func("hello") == "bonjour"
    assert t_func("missing") == "missing"


@patch("usbip_gui.common.languages.Path.exists")
@patch("builtins.open")
@patch("usbip_gui.common.languages.json.load")
def test_get_translator_other(
    mock_json_load: MagicMock, _mock_open: MagicMock, mock_exists: MagicMock
):
    """Test get_translator for other domains."""
    mock_exists.return_value = True
    # Return different dictionaries for the two json.load calls
    mock_json_load.side_effect = [
        {"common_key": "common_val"},
        {"domain_key": "domain_val"},
    ]

    t_func = get_translator("server")
    assert callable(t_func)
    assert t_func("domain_key") == "domain_val"
    assert t_func("common_key") == "common_val"
    assert t_func("missing") == "missing"


@patch("usbip_gui.common.languages.Path.exists")
@patch("builtins.open")
@patch("usbip_gui.common.languages.json.load")
def test_get_translator_fallback_to_en(
    mock_json_load: MagicMock, _mock_open: MagicMock, mock_exists: MagicMock
):
    """Test get_translator falling back to 'en' when lang file missing."""
    # Side effect: first path.exists() is False (missing file),
    #              second is True (en file exists)
    # Called twice inside get_translator("common"):
    # 1. common_translations -> False, True
    # 2. domain_translations (skipped since domain="common")
    mock_exists.side_effect = [False, True]
    mock_json_load.return_value = {"hello": "fallback_en_val"}

    t_func = get_translator("common")
    assert callable(t_func)
    assert t_func("hello") == "fallback_en_val"


@patch("usbip_gui.common.languages.Path.exists")
def test_get_translator_fallback_missing_too(mock_exists: MagicMock):
    """Test get_translator when both requested and 'en' files are missing."""
    mock_exists.return_value = False

    t_func = get_translator("common")
    assert callable(t_func)
    assert t_func("hello") == "hello"


@patch("usbip_gui.common.languages.Path.exists")
@patch("builtins.open")
@patch("usbip_gui.common.languages.json.load")
def test_get_translator_json_error(
    mock_json_load: MagicMock, _mock_open: MagicMock, mock_exists: MagicMock
):
    """Test get_translator handling JSONDecodeError."""

    mock_exists.return_value = True
    mock_json_load.side_effect = json.JSONDecodeError("msg", "doc", 0)

    t_func = get_translator("common")
    assert callable(t_func)
    assert t_func("hello") == "hello"


@patch("usbip_gui.common.languages.Locale.default")
def test_get_translator_locale_fallback(mock_locale_default: MagicMock):
    """Test locale language and territory fallback branches."""
    # 1. language but no territory
    mock_loc = MagicMock()
    mock_loc.language = "fr"
    mock_loc.territory = None
    mock_locale_default.return_value = mock_loc
    assert callable(get_translator("common"))

    # 2. no locale or no language
    mock_loc2 = MagicMock()
    mock_loc2.language = None
    mock_locale_default.return_value = mock_loc2
    assert callable(get_translator("common"))

    # 3. default returns None
    mock_locale_default.return_value = None
    assert callable(get_translator("common"))


@patch("usbip_gui.common.common.Path.mkdir")
@patch("usbip_gui.common.common.sys")
@patch.dict("os.environ", {"APPDATA": "/mock/appdata"})
def test_get_config_dir_windows(mock_sys: MagicMock, _mock_mkdir: MagicMock):
    """Test get_config_dir on Windows with APPDATA env var."""
    mock_sys.platform = "win32"

    config_dir = get_config_dir()
    assert config_dir == Path("/mock/appdata/usbip-gui")


@patch("usbip_gui.common.common.Path.mkdir")
@patch("usbip_gui.common.common.sys")
@patch("usbip_gui.common.common.Path.home")
@patch.dict("os.environ", {}, clear=True)
def test_get_config_dir_windows_no_appdata(
    mock_home: MagicMock, mock_sys: MagicMock, _mock_mkdir: MagicMock
):
    """Test get_config_dir on Windows without APPDATA env var."""
    mock_sys.platform = "win32"
    mock_home.return_value = Path("/mock/home")

    config_dir = get_config_dir()
    assert config_dir == Path("/mock/home/AppData/Roaming/usbip-gui")


@patch("usbip_gui.common.common.Path.mkdir")
@patch("usbip_gui.common.common.sys")
@patch.dict("os.environ", {"XDG_CONFIG_HOME": "/mock/xdg"})
def test_get_config_dir_linux_xdg(mock_sys: MagicMock, _mock_mkdir: MagicMock):
    """Test get_config_dir on Linux with XDG_CONFIG_HOME."""
    mock_sys.platform = "linux"

    config_dir = get_config_dir()
    assert config_dir == Path("/mock/xdg/usbip-gui")


@patch("usbip_gui.common.common.open")
@patch("usbip_gui.common.common.get_config_path")
def test_load_config_exception(mock_path: MagicMock, mock_open: MagicMock):
    """Test load_config exception handling."""
    mock_path.return_value.exists.return_value = True
    mock_open.side_effect = Exception("test")
    assert load_config() == {}


@patch("usbip_gui.common.common.open")
@patch("usbip_gui.common.common.get_config_path")
def test_save_config_exception(_mock_path: MagicMock, mock_open: MagicMock):
    """Test save_config exception handling."""
    mock_open.side_effect = Exception("test")
    save_config({"test": "data"})  # should not raise


def test_sortable_tree_widget_item_fallback():
    """Test SortableTreeWidgetItem fallback logic when no tree."""
    item1 = SortableTreeWidgetItem(["10"])
    item2 = SortableTreeWidgetItem(["2"])
    # Without tree, uses standard text comparison where "10" < "2"
    assert item1 < item2


def test_set_min_column_widths():
    """Test set_min_column_widths functionality."""
    tree = QTreeWidget()
    tree.setColumnCount(3)
    # The minimums to enforce
    min_widths = [100, 150, 200]

    set_min_column_widths(tree, min_widths)

    # Initial check: if width was below min, it should be set to min
    assert tree.columnWidth(0) == 100
    assert tree.columnWidth(1) == 150
    assert tree.columnWidth(2) == 200

    # Try resizing below minimum
    header = tree.header()
    assert header is not None

    # Resize section 1 to 50 (below 150)
    header.resizeSection(1, 50)
    # The callback should immediately force it back to 150
    assert tree.columnWidth(1) == 150

    # Resize section 1 to 300 (above 150)
    header.resizeSection(1, 300)
    # The callback should allow it
    assert tree.columnWidth(1) == 300

    # Test with no header mock or simply verify it completes without error
    tree_no_header = MagicMock(spec=QTreeWidget)
    tree_no_header.header.return_value = None
    set_min_column_widths(tree_no_header, [100])


def test_sortable_tree_widget_item_no_tree():
    """Test SortableTreeWidgetItem without a tree widget."""
    item1 = SortableTreeWidgetItem(["1-10"])
    item2 = SortableTreeWidgetItem(["1-3"])
    # Without a tree, it falls back to string comparison, where "1-10" < "1-3"
    assert item1 < item2


@patch("usbip_gui.common.common.re.split")
def test_sortable_tree_widget_item_type_error(mock_split: MagicMock):
    """Test SortableTreeWidgetItem fallback on TypeError."""
    tree = QTreeWidget()
    tree.setColumnCount(1)
    item1 = SortableTreeWidgetItem(["1-10"])
    item2 = SortableTreeWidgetItem(["1-3"])
    tree.addTopLevelItem(item1)
    tree.addTopLevelItem(item2)
    mock_split.side_effect = TypeError("Mocked TypeError")
    # It will fallback to super().__lt__,
    # which uses standard string comparison ("1-10" < "1-3") -> True
    assert item1 < item2


@patch("usbip_gui.common.languages.Locale.default")
def test_detect_system_language(mock_locale_default: MagicMock):
    """Test _detect_system_language with and without a territory."""
    mock_loc = MagicMock()
    mock_loc.language = "fr"
    mock_loc.territory = "CA"
    mock_locale_default.return_value = mock_loc
    assert _detect_system_language() == "fr_CA"

    mock_loc.territory = None
    assert _detect_system_language() == "fr"

    mock_locale_default.return_value = None
    assert _detect_system_language() == "en"


@patch("usbip_gui.common.languages.Locale.default")
def test_detect_system_language_exception(mock_locale_default: MagicMock):
    """Test _detect_system_language falls back to 'en' on exception."""
    mock_locale_default.side_effect = TypeError("boom")
    assert _detect_system_language() == "en"


@patch("usbip_gui.common.languages.save_config")
@patch("usbip_gui.common.languages.load_config")
def test_get_current_language_from_config(
    mock_load_config: MagicMock, _mock_save_config: MagicMock
):
    """Test get_current_language resolves and caches the saved language."""
    language_changed.current = None
    mock_load_config.return_value = {"language": "fr_CA"}
    assert get_current_language() == "fr_CA"
    # Cached on the shared state, so a second call skips load_config.
    mock_load_config.reset_mock()
    assert get_current_language() == "fr_CA"
    mock_load_config.assert_not_called()
    language_changed.current = None


@patch("usbip_gui.common.languages._detect_system_language")
@patch("usbip_gui.common.languages.load_config")
def test_get_current_language_detects_system(
    mock_load_config: MagicMock, mock_detect: MagicMock
):
    """Test get_current_language falls back to system detection."""
    language_changed.current = None
    mock_load_config.return_value = {}
    mock_detect.return_value = "en"
    assert get_current_language() == "en"
    mock_detect.assert_called_once()
    language_changed.current = None


@patch("usbip_gui.common.languages.save_config")
@patch("usbip_gui.common.languages.load_config")
def test_set_language(
    mock_load_config: MagicMock, mock_save_config: MagicMock
):
    """Test set_language updates state, env, config, and emits the signal."""
    mock_load_config.return_value = {}
    received: list[str] = []
    language_changed.changed.connect(received.append)  # pyright: ignore

    try:
        set_language("fr_CA")

        assert language_changed.current == "fr_CA"
        assert os.environ["LANGUAGE"] == "fr_CA"
        mock_save_config.assert_called_once_with({"language": "fr_CA"})
        assert received == ["fr_CA"]
    finally:
        language_changed.changed.disconnect(received.append)  # pyright: ignore
        language_changed.current = None
        os.environ.pop("LANGUAGE", None)
