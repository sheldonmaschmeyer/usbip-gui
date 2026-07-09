"""Tests for gui components."""

from unittest.mock import patch, MagicMock
from usbip_gui.gui.gui import UsbIpGui, start_app


@patch("usbip_gui.gui.gui.Tk")
@patch("usbip_gui.gui.gui.create_main_menu")
@patch("usbip_gui.gui.gui.Notebook")
@patch("usbip_gui.gui.gui.ServerTab")
@patch("usbip_gui.gui.gui.ClientTab")
@patch("usbip_gui.gui.gui.BooleanVar")
@patch("usbip_gui.gui.gui.StringVar")
def test_usb_ip_gui_init(
    _mock_string_var: MagicMock,
    _mock_bool_var: MagicMock,
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
    mock_menu.assert_called_once_with(gui)
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


@patch("usbip_gui.gui.gui.Tk")
@patch("usbip_gui.gui.gui.Notebook")
@patch("usbip_gui.gui.gui.ServerTab")
@patch("usbip_gui.gui.gui.ClientTab")
@patch("usbip_gui.gui.gui.BooleanVar")
@patch("usbip_gui.gui.gui.StringVar")
@patch("usbip_gui.gui.gui.create_main_menu")
def test_gui_update_tabs_and_defaults(
    _mock_menu: MagicMock,
    _mock_string_var: MagicMock,
    _mock_bool_var: MagicMock,
    _mock_client: MagicMock,
    _mock_server: MagicMock,
    mock_notebook_class: MagicMock,
    mock_tk: MagicMock,
):
    """Test update_tabs, default tab logic, and error handling in UsbIpGui."""
    from tkinter import TclError  # pylint: disable=import-outside-toplevel

    mock_notebook = mock_notebook_class.return_value

    # 1. Test update_tabs with TclErrors and broad exception
    mock_notebook.forget.side_effect = TclError("forget error")

    def mock_select_side_effect(*args: object, **kwargs: object):
        if not args and not kwargs:
            raise TclError("select error")

    mock_notebook.select.side_effect = mock_select_side_effect

    # Create UsbIpGui instance
    gui = UsbIpGui(mock_tk.return_value)

    # Mock show_server_var / show_client_var / default_tab_var
    gui.show_server_var = MagicMock()
    gui.show_client_var = MagicMock()
    gui.default_tab_var = MagicMock()

    # Make them return True/False/server/client
    gui.show_server_var.get.return_value = True
    gui.show_client_var.get.return_value = True
    gui.default_tab_var.get.return_value = "server"

    # Trigger exception on tabs() to hit the broad except clause
    mock_notebook.tabs.side_effect = Exception("tabs error")
    gui.update_tabs()

    # Test 2: update_tabs succeeding to restore tab (covers line 88)
    mock_notebook.tabs.side_effect = None
    mock_notebook.tabs.return_value = ["mock_tab"]
    mock_notebook.select.side_effect = None
    mock_notebook.select.return_value = "mock_tab"
    gui.update_tabs()

    # 2. Test apply_default_tab paths
    # Path 1: default_tab is server, show_server is True
    gui.default_tab_var.get.return_value = "server"
    gui.show_server_var.get.return_value = True
    gui.apply_default_tab()
    mock_notebook.select.assert_called_with(gui.server_tab.frame)

    # Path 2: default_tab is client, show_client is True
    gui.default_tab_var.get.return_value = "client"
    gui.show_client_var.get.return_value = True
    gui.show_server_var.get.return_value = False
    gui.apply_default_tab()
    mock_notebook.select.assert_called_with(gui.client_tab.frame)
