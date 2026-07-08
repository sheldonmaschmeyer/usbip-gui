"""Tests for the menu components."""

from unittest.mock import patch, MagicMock
from usbip_gui.gui.menu.menu import create_main_menu
from usbip_gui.gui.menu.about import show_about_dialog
from usbip_gui.gui.menu.language_switcher import toggle_language


@patch("usbip_gui.gui.menu.menu.Menu")
def test_create_main_menu(mock_menu: MagicMock):
    """Test creation of the main application menu."""
    mock_root = MagicMock()
    create_main_menu(mock_root)

    mock_menu.assert_called()
    assert mock_root.config.called


@patch("usbip_gui.gui.menu.about.tk.Toplevel")
@patch("usbip_gui.gui.menu.about.tk.Label")
@patch("usbip_gui.gui.menu.about.Button")
def test_show_about(
    _mock_button: MagicMock, _mock_label: MagicMock, mock_toplevel: MagicMock
):
    """Test the about dialog popup."""
    show_about_dialog()
    mock_toplevel.assert_called_once()
    mock_toplevel.return_value.title.assert_called_once()


@patch("usbip_gui.gui.menu.about.Button")
@patch("usbip_gui.gui.menu.about.tk.Toplevel")
def test_show_about_with_parent(
    mock_toplevel: MagicMock, _mock_button: MagicMock
):
    """Test show about dialog with parent."""
    parent = MagicMock()
    show_about_dialog(parent)
    mock_toplevel.return_value.transient.assert_called_once_with(parent)
    mock_toplevel.return_value.grab_set.assert_called_once()
    _mock_button.assert_called_once()


@patch("usbip_gui.gui.menu.language_switcher.os.execv")
@patch("usbip_gui.gui.menu.language_switcher.os.environ")
@patch("usbip_gui.gui.menu.language_switcher.sys")
def test_toggle_language(
    mock_sys: MagicMock, mock_env: MagicMock, mock_execv: MagicMock
):
    """Test toggling the language environment variables."""
    mock_sys.executable = "python"
    mock_sys.argv = ["main.py"]
    mock_env.get.return_value = "en"

    toggle_language()
    mock_execv.assert_called_once_with("python", ["python", "main.py"])
