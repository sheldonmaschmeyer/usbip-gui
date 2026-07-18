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


@patch("usbip_gui.gui.menu.menu.QActionGroup")
@patch("usbip_gui.gui.menu.menu.QAction")
def test_create_main_menu_defaults(
    _mock_action: MagicMock, _mock_group: MagicMock
):
    """Test creation of the main application menu with defaults."""
    mock_app = MagicMock()
    mock_app.default_tab_var = "server"
    create_main_menu(mock_app)

    mock_app.default_tab_var = "client"
    create_main_menu(mock_app)


@patch("usbip_gui.gui.menu.about.QDialog")
@patch("usbip_gui.gui.menu.about.QVBoxLayout")
@patch("usbip_gui.gui.menu.about.QLabel")
@patch("usbip_gui.gui.menu.about.QDialogButtonBox")
@patch("usbip_gui.gui.menu.about.connect_signal")
def test_show_about(
    _mock_connect: MagicMock,
    _mock_button_box: MagicMock,
    _mock_label: MagicMock,
    _mock_layout: MagicMock,
    mock_qdialog: MagicMock,
):
    """Test the about dialog popup."""
    show_about_dialog()
    mock_qdialog.assert_called_once()
    mock_qdialog.return_value.exec.assert_called_once()


@patch("usbip_gui.gui.menu.about.QDialog")
@patch("usbip_gui.gui.menu.about.QVBoxLayout")
@patch("usbip_gui.gui.menu.about.QLabel")
@patch("usbip_gui.gui.menu.about.QDialogButtonBox")
@patch("usbip_gui.gui.menu.about.connect_signal")
def test_show_about_with_parent(
    _mock_connect: MagicMock,
    _mock_button_box: MagicMock,
    _mock_label: MagicMock,
    _mock_layout: MagicMock,
    mock_qdialog: MagicMock,
):
    """Test show about dialog with parent."""
    parent = MagicMock()
    show_about_dialog(parent)
    mock_qdialog.assert_called_once_with(parent)
    mock_qdialog.return_value.exec.assert_called_once()


@patch("usbip_gui.gui.menu.language_switcher.set_language")
@patch("usbip_gui.gui.menu.language_switcher.get_current_language")
def test_toggle_language(
    mock_get_current_language: MagicMock, mock_set_language: MagicMock
):
    """Test toggling the language."""
    mock_get_current_language.return_value = "en"

    toggle_language()
    mock_set_language.assert_called_once_with("fr_CA")


@patch("usbip_gui.gui.menu.language_switcher.set_language")
@patch("usbip_gui.gui.menu.language_switcher.get_current_language")
def test_toggle_language_back_to_english(
    mock_get_current_language: MagicMock, mock_set_language: MagicMock
):
    """Test toggling the language back to English from French."""
    mock_get_current_language.return_value = "fr_CA"

    toggle_language()
    mock_set_language.assert_called_once_with("en")
