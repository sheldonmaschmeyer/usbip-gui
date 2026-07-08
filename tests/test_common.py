"""Tests for the common gui components."""

from unittest.mock import patch, MagicMock
from usbip_gui.gui.common import (
    TunnelState,
    cleanup_tunnels,
    tunnel_state,
    get_translator,
    ToolTip,
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


@patch("usbip_gui.gui.common.tk.Toplevel")
@patch("usbip_gui.gui.common.tk.Label")
def test_tooltip(mock_label: MagicMock, mock_top: MagicMock):
    """Test ToolTip functionality."""
    widget = MagicMock()
    widget.winfo_rootx.return_value = 100
    widget.winfo_rooty.return_value = 100

    tt = ToolTip(widget, "test")
    widget.bind.assert_any_call("<Enter>", tt.show_tooltip)
    widget.bind.assert_any_call("<Leave>", tt.hide_tooltip)

    tt.show_tooltip()
    mock_top.assert_called_once_with(widget)
    mock_label.assert_called_once()
    assert tt.tooltip_window is not None

    # second call should return early
    mock_top.reset_mock()
    tt.show_tooltip()
    mock_top.assert_not_called()

    # hide tooltip
    tt.hide_tooltip()
    mock_top.return_value.destroy.assert_called_once()
    assert tt.tooltip_window is None

    # hide when None
    tt.hide_tooltip()
