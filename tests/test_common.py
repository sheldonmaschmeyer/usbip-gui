"""Tests for the common gui components."""

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
@patch("usbip_gui.gui.common.gettext.translation")
def test_get_translator_common(mock_trans: MagicMock, mock_exists: MagicMock):
    """Test get_translator for common domain."""
    mock_exists.return_value = True
    mock_trans.return_value.gettext = "mocked"
    t_func = get_translator("common")
    assert t_func == "mocked"
    mock_trans.assert_called_once()


@patch("usbip_gui.gui.common.Path.exists")
@patch("usbip_gui.gui.common.gettext.translation")
def test_get_translator_other(mock_trans: MagicMock, mock_exists: MagicMock):
    """Test get_translator for other domains."""
    mock_exists.return_value = False
    mock_trans.return_value.gettext = "mocked"
    t_func = get_translator("server")
    assert t_func == "mocked"
    assert mock_trans.call_count == 2
    mock_trans.return_value.add_fallback.assert_called_once()


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


def test_sortable_tree_widget_item_no_tree():
    """Test SortableTreeWidgetItem without a tree widget."""
    item1 = SortableTreeWidgetItem(["1-10"])
    item2 = SortableTreeWidgetItem(["1-3"])
    # Without a tree, it falls back to string comparison, where "1-10" < "1-3"
    assert item1 < item2
    assert item2 >= item1


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
