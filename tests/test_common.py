"""Tests for the common gui components."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from PyQt6.QtWidgets import QTreeWidget
from usbip_gui.gui.common import (
    TunnelState,
    cleanup_tunnels,
    tunnel_state,
    get_translator,
    get_config_dir,
    load_config,
    save_config,
    SortableTreeWidgetItem,
    set_min_column_widths,
)


def test_tunnel_state_initialization():
    """Test that TunnelState initializes with empty/None processes."""
    state = TunnelState()
    assert state.server_process is None
    assert not state.client_processes


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


@patch("usbip_gui.gui.common.Path.exists")
@patch("builtins.open")
@patch("usbip_gui.gui.common.json.load")
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


@patch("usbip_gui.gui.common.Path.exists")
@patch("builtins.open")
@patch("usbip_gui.gui.common.json.load")
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


@patch("usbip_gui.gui.common.Path.exists")
@patch("builtins.open")
@patch("usbip_gui.gui.common.json.load")
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


@patch("usbip_gui.gui.common.Path.exists")
def test_get_translator_fallback_missing_too(mock_exists: MagicMock):
    """Test get_translator when both requested and 'en' files are missing."""
    mock_exists.return_value = False

    t_func = get_translator("common")
    assert callable(t_func)
    assert t_func("hello") == "hello"


@patch("usbip_gui.gui.common.Path.exists")
@patch("builtins.open")
@patch("usbip_gui.gui.common.json.load")
def test_get_translator_json_error(
    mock_json_load: MagicMock, _mock_open: MagicMock, mock_exists: MagicMock
):
    """Test get_translator handling JSONDecodeError."""

    mock_exists.return_value = True
    mock_json_load.side_effect = json.JSONDecodeError("msg", "doc", 0)

    t_func = get_translator("common")
    assert callable(t_func)
    assert t_func("hello") == "hello"


@patch("usbip_gui.gui.common.Locale.default")
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


@patch("usbip_gui.gui.common.Path.mkdir")
@patch("usbip_gui.gui.common.sys")
@patch.dict("os.environ", {"APPDATA": "/mock/appdata"})
def test_get_config_dir_windows(mock_sys: MagicMock, _mock_mkdir: MagicMock):
    """Test get_config_dir on Windows with APPDATA env var."""
    mock_sys.platform = "win32"

    config_dir = get_config_dir()
    assert config_dir == Path("/mock/appdata/usbip-gui")


@patch("usbip_gui.gui.common.Path.mkdir")
@patch("usbip_gui.gui.common.sys")
@patch("usbip_gui.gui.common.Path.home")
@patch.dict("os.environ", {}, clear=True)
def test_get_config_dir_windows_no_appdata(
    mock_home: MagicMock, mock_sys: MagicMock, _mock_mkdir: MagicMock
):
    """Test get_config_dir on Windows without APPDATA env var."""
    mock_sys.platform = "win32"
    mock_home.return_value = Path("/mock/home")

    config_dir = get_config_dir()
    assert config_dir == Path("/mock/home/AppData/Roaming/usbip-gui")


@patch("usbip_gui.gui.common.Path.mkdir")
@patch("usbip_gui.gui.common.sys")
@patch.dict("os.environ", {"XDG_CONFIG_HOME": "/mock/xdg"})
def test_get_config_dir_linux_xdg(mock_sys: MagicMock, _mock_mkdir: MagicMock):
    """Test get_config_dir on Linux with XDG_CONFIG_HOME."""
    mock_sys.platform = "linux"

    config_dir = get_config_dir()
    assert config_dir == Path("/mock/xdg/usbip-gui")


@patch("usbip_gui.gui.common.open")
@patch("usbip_gui.gui.common.get_config_path")
def test_load_config_exception(mock_path: MagicMock, mock_open: MagicMock):
    """Test load_config exception handling."""
    mock_path.return_value.exists.return_value = True
    mock_open.side_effect = Exception("test")
    assert load_config() == {}


@patch("usbip_gui.gui.common.open")
@patch("usbip_gui.gui.common.get_config_path")
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


@patch("usbip_gui.gui.common.re.split")
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
