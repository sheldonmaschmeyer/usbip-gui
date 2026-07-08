"""Tests for gui components."""

from unittest.mock import patch, MagicMock
from usbip_gui.gui.gui import UsbIpGui, start_app


@patch("usbip_gui.gui.gui.Tk")
@patch("usbip_gui.gui.gui.create_main_menu")
@patch("usbip_gui.gui.gui.Notebook")
@patch("usbip_gui.gui.gui.ServerTab")
@patch("usbip_gui.gui.gui.ClientTab")
def test_usb_ip_gui_init(
    _mock_client: MagicMock,
    _mock_server: MagicMock,
    mock_notebook: MagicMock,
    mock_menu: MagicMock,
    mock_tk: MagicMock,
):
    """Test the initialization of the UsbIpGui class."""
    mock_root = mock_tk.return_value
    gui = UsbIpGui(mock_root)

    mock_root.wm_title.assert_called_once()
    mock_root.geometry.assert_called_once()
    mock_menu.assert_called_once_with(mock_root)
    mock_notebook.assert_called_once_with(mock_root)

    _mock_server.assert_called_once()
    _mock_client.assert_called_once()

    assert gui.root == mock_root


@patch("usbip_gui.gui.gui.Tk")
@patch("usbip_gui.gui.gui.Style")
@patch("usbip_gui.gui.gui.Label")
@patch("usbip_gui.gui.gui.UsbIpGui")
@patch("usbip_gui.gui.gui.os.path.exists", return_value=False)
@patch("usbip_gui.gui.gui.tkfont.nametofont")
@patch("usbip_gui.gui.gui.subprocess.run")
# pylint: disable=too-many-arguments,too-many-positional-arguments
def test_start_app(
    _mock_run: MagicMock,
    _mock_font: MagicMock,
    _mock_exists: MagicMock,
    mock_gui: MagicMock,
    _mock_label: MagicMock,
    mock_style: MagicMock,
    mock_tk: MagicMock,
):
    """Test the start_app function."""
    start_app()

    mock_tk.assert_called_once()
    mock_root = mock_tk.return_value
    mock_style.assert_called_once_with(mock_root)

    # Check if mainloop was called
    mock_root.mainloop.assert_called_once()

    # Check if UsbIpGui was instantiated
    mock_gui.assert_called_once_with(mock_root)


@patch("usbip_gui.gui.gui.Tk")
@patch("usbip_gui.gui.gui.Style")
@patch("usbip_gui.gui.gui.os.path.exists")
@patch("usbip_gui.gui.gui.subprocess.run")
@patch("usbip_gui.gui.gui.tkfont.nametofont")
@patch("usbip_gui.gui.gui.Label")
@patch("usbip_gui.gui.gui.UsbIpGui")
def test_start_app_clam_and_subprocess(
    _mock_gui: MagicMock,
    _mock_label: MagicMock,
    _mock_font: MagicMock,
    mock_run: MagicMock,
    mock_exists: MagicMock,
    mock_style_class: MagicMock,
    _mock_tk: MagicMock,
):
    """Test start app with clam theme and missing kernel modules."""
    mock_style = MagicMock()
    mock_style.theme_names.return_value = ["clam", "default"]
    mock_style_class.return_value = mock_style

    # First call is script_path, subsequent are modules
    def mock_exists_side_effect(path: str) -> bool:
        return not path.startswith("/sys/module/")

    mock_exists.side_effect = mock_exists_side_effect

    start_app()

    mock_style.theme_use.assert_called_once_with("clam")
    mock_run.assert_called_once()
