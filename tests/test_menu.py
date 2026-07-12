"""Tests for the menu components."""

from unittest.mock import MagicMock, patch

from usbip_gui.gui.menu.about import show_about_dialog
from usbip_gui.gui.menu.language_switcher import toggle_language
from usbip_gui.gui.menu.menu import create_main_menu


@patch("usbip_gui.gui.menu.menu.QActionGroup")
@patch("usbip_gui.gui.menu.menu.QAction")
def test_create_main_menu(_mock_action: MagicMock, _mock_group: MagicMock):
    """Test creation of the main application menu."""
    mock_app = MagicMock()
    create_main_menu(mock_app)

    mock_app.root.menuBar.assert_called_once()


@patch("usbip_gui.gui.menu.about.QMessageBox.about")
def test_show_about(mock_about: MagicMock):
    """Test the about dialog popup."""
    show_about_dialog()
    mock_about.assert_called_once()


@patch("usbip_gui.gui.menu.about.QMessageBox.about")
def test_show_about_with_parent(mock_about: MagicMock):
    """Test show about dialog with parent."""
    parent = MagicMock()
    show_about_dialog(parent)
    mock_about.assert_called_once()
    assert mock_about.call_args[0][0] == parent


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
