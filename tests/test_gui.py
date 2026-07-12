"""Tests for gui components."""

from unittest.mock import MagicMock, patch

from usbip_gui.gui.gui import UsbIpGui, start_app


@patch("usbip_gui.gui.gui.QTabWidget")
@patch("usbip_gui.gui.gui.ServerTab")
@patch("usbip_gui.gui.gui.ClientTab")
@patch("usbip_gui.gui.gui.create_main_menu")
def test_usb_ip_gui_init(
    mock_menu: MagicMock,
    mock_client: MagicMock,
    mock_server: MagicMock,
    mock_notebook: MagicMock,
):
    """Test the initialization of the UsbIpGui class."""
    mock_root = MagicMock()
    mock_notebook.return_value.currentIndex.return_value = 0
    mock_notebook.return_value.indexOf.return_value = 0
    gui = UsbIpGui(mock_root)

    mock_root.setWindowTitle.assert_called_once()
    mock_root.resize.assert_called_once()
    mock_menu.assert_called_once_with(gui)
    mock_notebook.assert_called_once_with(mock_root)
    mock_server.assert_called_once()
    mock_client.assert_called_once()
    assert gui.root == mock_root


@patch("usbip_gui.gui.gui.QApplication")
@patch("usbip_gui.gui.gui.QMainWindow")
@patch("usbip_gui.gui.gui.UsbIpGui")
@patch("usbip_gui.gui.gui.sys")
@patch("usbip_gui.gui.gui.os.path.exists", return_value=False)
@patch("usbip_gui.gui.gui.subprocess.run")
def test_start_app(
    _mock_run: MagicMock,
    _mock_exists: MagicMock,
    _mock_sys: MagicMock,
    mock_gui: MagicMock,
    mock_qmain: MagicMock,
    mock_qapp: MagicMock,
):
    """Test the start_app function."""
    start_app()

    mock_qapp.assert_called_once()
    mock_qmain.assert_called_once()
    mock_root = mock_qmain.return_value
    mock_gui.assert_called_once_with(mock_root)
    mock_root.show.assert_called_once()


@patch("usbip_gui.gui.gui.QApplication")
@patch("usbip_gui.gui.gui.QMainWindow")
@patch("usbip_gui.gui.gui.UsbIpGui")
@patch("usbip_gui.gui.gui.sys")
@patch("usbip_gui.gui.gui.os.path.exists")
@patch("usbip_gui.gui.gui.subprocess.run")
def test_start_app_clam_and_subprocess(
    mock_run: MagicMock,
    mock_exists: MagicMock,
    _mock_sys: MagicMock,
    _mock_gui: MagicMock,
    _mock_qmain: MagicMock,
    _mock_qapp: MagicMock,
):
    """Test start app with missing kernel modules."""

    def mock_exists_side_effect(path: str) -> bool:
        return not path.startswith("/sys/module/")

    mock_exists.side_effect = mock_exists_side_effect

    start_app()
    mock_run.assert_called_once()


@patch("usbip_gui.gui.gui.QTabWidget")
@patch("usbip_gui.gui.gui.ServerTab")
@patch("usbip_gui.gui.gui.ClientTab")
@patch("usbip_gui.gui.gui.create_main_menu")
def test_gui_update_tabs_and_defaults(
    _mock_menu: MagicMock,
    _mock_client: MagicMock,
    _mock_server: MagicMock,
    mock_notebook_class: MagicMock,
):
    """Test update_tabs, default tab logic, and error handling in UsbIpGui."""
    mock_notebook = mock_notebook_class.return_value
    mock_notebook.currentIndex.return_value = 0
    mock_notebook.indexOf.return_value = 0
    mock_root = MagicMock()
    gui = UsbIpGui(mock_root)

    gui.show_server_var = True
    gui.show_client_var = True
    gui.default_tab_var = "server"
    mock_notebook.widget.return_value = None

    gui.update_tabs()
    assert len(mock_notebook.addTab.call_args_list) >= 2

    # Test apply_default_tab paths
    gui.default_tab_var = "server"
    gui.show_server_var = True
    mock_notebook.indexOf.return_value = 0
    gui.apply_default_tab()
    mock_notebook.setCurrentIndex.assert_called_with(0)

    gui.default_tab_var = "client"
    gui.show_client_var = True
    gui.show_server_var = False
    mock_notebook.indexOf.return_value = 1
    gui.apply_default_tab()
    mock_notebook.setCurrentIndex.assert_called_with(1)
