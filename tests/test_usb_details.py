"""Tests for usb_details script."""

import json
import sys
from unittest.mock import MagicMock, patch

import runpy
import pytest
import usb.core

from usbip_gui.product_detection.usb_details import (
    _resolve_inf_string,  # pyright: ignore[reportPrivateUsage]
    get_string,
    get_strings_from_registry,
    main,
    matches_device,
    parse_bus_id,
)


def test_parse_bus_id():
    """Test parse_bus_id."""
    assert parse_bus_id("1-2.3") == (1, (2, 3))
    assert parse_bus_id("2-1") == (2, (1,))
    assert parse_bus_id("invalid") == (None, ())
    assert parse_bus_id("a-b.c") == (None, ())
    assert parse_bus_id("1-") == (1, ())


def test_matches_device():
    """Test matches_device."""
    dev = MagicMock()
    dev.bus = 1
    dev.port_numbers = (2, 3)

    assert matches_device(dev, "1-2.3")
    assert not matches_device(dev, "2-2.3")
    assert not matches_device(dev, "1-2.4")

    dev.port_numbers = None
    dev.port_number = 4
    assert matches_device(dev, "1-4")
    assert not matches_device(dev, "1-5")

    dev.port_number = None
    assert not matches_device(dev, "1-4")

    # Invalid bus id
    assert not matches_device(dev, "invalid")


def test_get_string():
    """Test get_string."""
    dev = MagicMock()
    assert get_string(dev, 0) == ""

    with patch(
        "usbip_gui.product_detection.usb_details.usb.util.get_string"
    ) as m_get:
        m_get.return_value = "TestString"
        assert get_string(dev, 1) == "TestString"

        m_get.side_effect = ValueError("Failed")
        assert get_string(dev, 1) == ""


def test_resolve_inf_string():
    """Test _resolve_inf_string."""
    assert (
        _resolve_inf_string("@oem5.inf,%key%;Actual String") == "Actual String"
    )
    assert _resolve_inf_string("Actual String") == "Actual String"


@patch("sys.platform", "win32")
def test_get_strings_from_registry_win32():
    """Test get_strings_from_registry on mocked win32."""
    winreg_mock = MagicMock()

    # We must patch winreg since it's only imported on Windows
    sys.modules["winreg"] = winreg_mock

    # Mock registry lookup structure
    key_mock = MagicMock()
    inst_mock = MagicMock()

    winreg_mock.OpenKey.return_value.__enter__.side_effect = [
        key_mock,
        inst_mock,
    ]
    winreg_mock.EnumKey.side_effect = ["instance1", OSError("No more entries")]

    def mock_query_value(_inst: object, name: str) -> tuple[str, int]:
        if name == "Mfg":
            return ("@oem.inf,%mfg%;Mock Mfg", 1)
        if name == "DeviceDesc":
            return ("Mock Desc", 1)
        if name == "BusReportedDeviceDesc":
            return ("Mock Bus Desc", 1)
        raise OSError()

    winreg_mock.QueryValueEx.side_effect = mock_query_value

    mfg, desc = get_strings_from_registry(0x1234, 0x5678)
    assert mfg == "Mock Mfg"
    assert desc == "Mock Desc"

    # Test missing winreg module
    del sys.modules["winreg"]


@patch("sys.platform", "linux")
def test_get_strings_from_registry_linux():
    """Test get_strings_from_registry on non-win32."""
    assert get_strings_from_registry(0x1234, 0x5678) == ("", "")


@patch("sys.platform", "win32")
def test_main_vid_pid_win32(capsys: pytest.CaptureFixture[str]):
    """Test main with --vid-pid on mocked win32."""
    with patch("sys.argv", ["usb_details.py", "--vid-pid", "1234:5678"]):
        with patch(
            "usbip_gui.product_detection.usb_details.get_strings_from_registry"
        ) as m_reg:
            m_reg.return_value = ("TestMfg", "TestProd")
            main()
            out = capsys.readouterr().out
            data = json.loads(out)
            assert data["manufacturer"] == "TestMfg"
            assert data["product"] == "TestProd"


@patch("sys.platform", "win32")
def test_main_vid_pid_win32_exception(capsys: pytest.CaptureFixture[str]):
    """Test main with --vid-pid raising exception."""
    with patch("sys.argv", ["usb_details.py", "--vid-pid", "1234"]):
        main()
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "not enough values to unpack" in data["error"]


@patch("sys.platform", "linux")
def test_main_vid_pid_linux(capsys: pytest.CaptureFixture[str]):
    """Test main with --vid-pid on non-win32."""
    with patch("sys.argv", ["usb_details.py", "--vid-pid", "1234:5678"]):
        main()
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "Registry lookup only supported on Windows" in data["error"]


def test_main_bus_id_success(capsys: pytest.CaptureFixture[str]):
    """Test main with bus id."""
    with patch("sys.argv", ["usb_details.py", "1-2.3"]):
        with patch(
            "usbip_gui.product_detection.usb_details.usb.core.find"
        ) as m_find:
            dev = MagicMock()
            dev.iManufacturer = 1
            dev.iProduct = 2
            m_find.return_value = dev

            with patch(
                "usbip_gui.product_detection.usb_details.get_string"
            ) as m_get:
                m_get.side_effect = ["TestMfg", "TestProd"]
                main()
                out = capsys.readouterr().out
                data = json.loads(out)
                assert data["manufacturer"] == "TestMfg"
                assert data["product"] == "TestProd"


def test_main_bus_id_not_found(capsys: pytest.CaptureFixture[str]):
    """Test main with bus id not found."""
    with patch("sys.argv", ["usb_details.py", "1-2.3"]):
        with patch(
            "usbip_gui.product_detection.usb_details.usb.core.find"
        ) as m_find:
            m_find.return_value = None
            main()
            out = capsys.readouterr().out
            data = json.loads(out)
            assert "Could not find USB device" in data["error"]


def test_main_exceptions(capsys: pytest.CaptureFixture[str]):
    """Test main exception handling."""
    with patch("sys.argv", ["usb_details.py", "1-2.3"]):
        with patch(
            "usbip_gui.product_detection.usb_details.usb.core.find"
        ) as m_find:
            m_find.side_effect = usb.core.NoBackendError()
            main()
            out = capsys.readouterr().out
            data = json.loads(out)
            assert "No PyUSB backend found" in data["error"]

            m_find.side_effect = usb.core.USBError("USB error", 123, 0)
            main()
            out = capsys.readouterr().out
            data = json.loads(out)
            assert "USB error" in data["error"]

            m_find.side_effect = Exception("Generic error")
            main()
            out = capsys.readouterr().out
            data = json.loads(out)
            assert "Generic error" in data["error"]


def test_main_registry_fallback_win32(capsys: pytest.CaptureFixture[str]):
    """Test fallback to registry on win32."""
    with patch("sys.argv", ["usb_details.py", "1-2.3"]):
        with patch("sys.platform", "win32"):
            with patch(
                "usbip_gui.product_detection.usb_details.usb.core.find"
            ) as m_find:
                dev = MagicMock()
                dev.iManufacturer = 0
                dev.iProduct = 0
                dev.idVendor = 0x1234
                dev.idProduct = 0x5678
                m_find.return_value = dev

                with patch(
                    "usbip_gui.product_detection.usb_details.get_string",
                    return_value="",
                ):
                    with patch(
                        "usbip_gui.product_detection.usb_details"
                        ".get_strings_from_registry"
                    ) as m_reg:
                        m_reg.return_value = ("RegMfg", "RegProd")
                        main()
                        out = capsys.readouterr().out
                        data = json.loads(out)
                        assert data["manufacturer"] == "RegMfg"
                        assert data["product"] == "RegProd"

                # Test missing vid/pid
                dev.idVendor = None
                with patch(
                    "usbip_gui.product_detection.usb_details.get_string",
                    return_value="",
                ):
                    main()
                    out = capsys.readouterr().out
                    data = json.loads(out)
                    assert data["manufacturer"] == ""
                    assert data["product"] == ""


@patch("sys.platform", "win32")
def test_get_strings_from_registry_win32_branches():
    """Test deep branches of get_strings_from_registry."""
    winreg_mock = MagicMock()
    sys.modules["winreg"] = winreg_mock
    key_mock = MagicMock()
    inst_mock = MagicMock()

    # Branch 1.5: Empty mfg and desc
    winreg_mock.OpenKey.return_value.__enter__.side_effect = [
        key_mock,
        inst_mock,
    ]
    winreg_mock.EnumKey.side_effect = ["instance1", OSError("No more entries")]

    def mock_qv_empty(_inst: object, name: str) -> tuple[str, int]:
        if name == "Mfg":
            return ("", 1)
        if name == "DeviceDesc":
            return ("", 1)
        if name == "BusReportedDeviceDesc":
            return ("", 1)
        raise OSError()

    winreg_mock.QueryValueEx.side_effect = mock_qv_empty
    assert get_strings_from_registry(0x1234, 0x5678) == ("", "")

    # Branch 1.6: inner OpenKey raises OSError
    winreg_mock.OpenKey.return_value.__enter__.side_effect = [
        key_mock,
        OSError(),
    ]
    winreg_mock.EnumKey.side_effect = ["instance1", OSError("No more entries")]
    assert get_strings_from_registry(0x1234, 0x5678) == ("", "")

    # Branch 1.7: QueryValueEx raises OSError
    winreg_mock.OpenKey.return_value.__enter__.side_effect = [
        key_mock,
        inst_mock,
    ]
    winreg_mock.EnumKey.side_effect = ["instance1", OSError("No more entries")]
    winreg_mock.QueryValueEx.side_effect = OSError()
    assert get_strings_from_registry(0x1234, 0x5678) == ("", "")

    # Branch 1: Generic mfg, generic desc, valid first word
    winreg_mock.OpenKey.return_value.__enter__.side_effect = [
        key_mock,
        inst_mock,
    ]
    winreg_mock.EnumKey.side_effect = ["instance1", OSError("No more entries")]

    def mock_qv(_inst: object, name: str) -> tuple[str, int]:
        if name == "Mfg":
            return ("Generic", 1)
        if name == "DeviceDesc":
            return ("Generic", 1)
        if name == "BusReportedDeviceDesc":
            return ("Logitech Mouse", 1)
        raise OSError()

    winreg_mock.QueryValueEx.side_effect = mock_qv

    mfg, desc = get_strings_from_registry(0x1234, 0x5678)
    assert mfg == "Logitech"
    assert desc == "Logitech Mouse"

    del sys.modules["winreg"]


@patch("sys.platform", "win32")
def test_get_strings_from_registry_win32_branches_2():
    """Test remaining deep branches of get_strings_from_registry."""
    winreg_mock = MagicMock()
    sys.modules["winreg"] = winreg_mock
    key_mock = MagicMock()
    inst_mock = MagicMock()

    # Branch 2: Generic mfg, generic desc, invalid first word (usb)
    winreg_mock.OpenKey.return_value.__enter__.side_effect = [
        key_mock,
        inst_mock,
    ]
    winreg_mock.EnumKey.side_effect = ["instance1", OSError("No more entries")]

    def mock_qv2(_inst: object, name: str) -> tuple[str, int]:
        if name == "Mfg":
            return ("Generic", 1)
        if name == "DeviceDesc":
            return ("Generic", 1)
        if name == "BusReportedDeviceDesc":
            return ("usb Mouse", 1)
        raise OSError()

    winreg_mock.QueryValueEx.side_effect = mock_qv2

    mfg, desc = get_strings_from_registry(0x1234, 0x5678)
    assert mfg == "Generic"
    assert desc == "Generic"

    # Branch 3: Non-generic mfg, desc starts with usb
    winreg_mock.OpenKey.return_value.__enter__.side_effect = [
        key_mock,
        inst_mock,
    ]
    winreg_mock.EnumKey.side_effect = ["instance1", OSError("No more entries")]

    def mock_qv3(_inst: object, name: str) -> tuple[str, int]:
        if name == "Mfg":
            return ("Apple", 1)
        if name == "DeviceDesc":
            return ("USB Keyboard", 1)
        if name == "BusReportedDeviceDesc":
            return ("Apple Keyboard", 1)
        raise OSError()

    winreg_mock.QueryValueEx.side_effect = mock_qv3

    mfg, desc = get_strings_from_registry(0x1234, 0x5678)
    assert mfg == "Apple"
    assert desc == "Apple Keyboard"

    # Branch 5: Non-generic mfg, desc starts with usb
    winreg_mock.OpenKey.return_value.__enter__.side_effect = [
        key_mock,
        inst_mock,
    ]
    winreg_mock.EnumKey.side_effect = ["instance1", OSError("No more entries")]

    def mock_qv_usb_desc(_inst: object, name: str) -> tuple[str, int]:
        if name == "Mfg":
            return ("Logitech", 1)
        if name == "DeviceDesc":
            return ("USB Mouse", 1)
        if name == "BusReportedDeviceDesc":
            return ("Logitech USB Mouse", 1)
        raise OSError()

    winreg_mock.QueryValueEx.side_effect = mock_qv_usb_desc

    mfg, desc = get_strings_from_registry(0x1234, 0x5678)
    assert mfg == "Logitech"
    assert desc == "Logitech USB Mouse"

    # Branch 6: Generic mfg, desc generic, first word of bus generic
    winreg_mock.OpenKey.return_value.__enter__.side_effect = [
        key_mock,
        inst_mock,
    ]
    winreg_mock.EnumKey.side_effect = ["instance1", OSError("No more entries")]

    def mock_qv_generic_bus(_inst: object, name: str) -> tuple[str, int]:
        if name == "Mfg":
            return ("Generic", 1)
        if name == "DeviceDesc":
            return ("Generic", 1)
        if name == "BusReportedDeviceDesc":
            return ("generic Mouse", 1)
        raise OSError()

    winreg_mock.QueryValueEx.side_effect = mock_qv_generic_bus

    mfg, desc = get_strings_from_registry(0x1234, 0x5678)
    assert mfg == "Generic"
    assert desc == "generic Mouse"

    # Branch 4: OSError at outer OpenKey
    winreg_mock.OpenKey.side_effect = OSError()
    assert get_strings_from_registry(0x1234, 0x5678) == ("", "")

    del sys.modules["winreg"]


def test_name_main():
    """Test module entrypoint block."""
    with patch(
        "sys.argv", ["usbip_gui/product_detection/usb_details.py", "1-2.3"]
    ):
        with patch(
            "usbip_gui.product_detection.usb_details.usb.core.find"
        ) as m_find:
            m_find.return_value = None
            runpy.run_path(
                "usbip_gui/product_detection/usb_details.py",
                run_name="__main__",
            )
