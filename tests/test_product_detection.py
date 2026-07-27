"""Tests for product detection module."""

import json
import sys
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from usbip_gui.product_detection.heuristics import is_generic_manufacturer
from usbip_gui.product_detection.product_detection import (
    ItemUpdater,
    SortableTreeWidgetItem,
    enrich_device_item,
    enrich_remote_device_item,
    extract_unknown_product_suffix,
    is_unknown_product,
    read_local_usb_descriptor_details,
    read_windows_registry_usb_descriptor_details,
    usb_details_script_path,
)
from usbip_gui.product_detection.usb_details import (
    _resolve_inf_string,  # pyright: ignore[reportPrivateUsage]
    get_strings_from_registry,
    main,
    matches_device,
    parse_bus_id,
)


def test_is_generic_manufacturer():
    """Test is_generic_manufacturer."""
    assert not is_generic_manufacturer("")
    assert not is_generic_manufacturer("Apple")
    assert is_generic_manufacturer("Microsoft")
    assert is_generic_manufacturer("(Standard system devices)")
    assert is_generic_manufacturer("Generic")


def test_is_unknown_product():
    """Test is_unknown_product."""
    assert is_unknown_product("Unknown product")
    assert is_unknown_product("unknown product (1234:5678)")
    assert not is_unknown_product("Apple iPhone")


def test_extract_unknown_product_suffix():
    """Test extract_unknown_product_suffix."""
    assert (
        extract_unknown_product_suffix("unknown product (1234:5678)")
        == " (1234:5678)"
    )
    assert extract_unknown_product_suffix("unknown product") == ""


def test_usb_details_script_path():
    """Test usb_details_script_path."""
    assert "usb_details.py" in usb_details_script_path()


@patch("usbip_gui.product_detection.product_detection.sys.platform", "win32")
@patch("usbip_gui.product_detection.product_detection.subprocess.run")
def test_read_local_usb_descriptor_details(mock_run: MagicMock):
    """Test read_local_usb_descriptor_details."""
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = json.dumps(
        {"manufacturer": "Man", "product": "Prod", "error": ""}
    )
    assert read_local_usb_descriptor_details("1-1") == ("Man", "Prod")

    mock_run.return_value.returncode = 1
    mock_run.return_value.stdout = json.dumps({"error": "Failed"})
    with pytest.raises(OSError):
        read_local_usb_descriptor_details("1-1")

    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = "invalid json"
    with pytest.raises(OSError):
        read_local_usb_descriptor_details("1-1")


@patch("usbip_gui.product_detection.product_detection.sys.platform", "win32")
@patch("usbip_gui.product_detection.product_detection.subprocess.run")
def test_read_windows_registry_usb_descriptor_details(mock_run: MagicMock):
    """Test read_windows_registry_usb_descriptor_details."""
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = json.dumps(
        {"manufacturer": "Man", "product": "Prod", "error": ""}
    )
    assert read_windows_registry_usb_descriptor_details("1234:5678") == (
        "Man",
        "Prod",
    )

    # Test error in payload
    mock_run.return_value.stdout = json.dumps({"error": "Failed"})
    assert read_windows_registry_usb_descriptor_details("1234:5678") == (
        "",
        "",
    )

    # Test invalid json
    mock_run.return_value.stdout = "invalid"
    assert read_windows_registry_usb_descriptor_details("1234:5678") == (
        "",
        "",
    )

    # Test empty payload
    mock_run.return_value.stdout = ""
    assert read_windows_registry_usb_descriptor_details("1234:5678") == (
        "",
        "",
    )

    # Test non-zero returncode
    mock_run.return_value.returncode = 1
    assert read_windows_registry_usb_descriptor_details("1234:5678") == (
        "",
        "",
    )


def test_enrich_device_item():
    """Test enrich_device_item."""
    item = MagicMock()
    updater = MagicMock()

    def mock_thread_init(*_args: object, **kwargs: object):
        mock_t = MagicMock()
        mock_t.start.side_effect = kwargs["target"]
        return mock_t

    with patch(
        "usbip_gui.product_detection.product_detection.threading.Thread",
        side_effect=mock_thread_init,
    ):
        with patch(
            "usbip_gui.product_detection.product_detection"
            ".read_local_usb_descriptor_details"
        ) as mock_read:
            # Test normal
            mock_read.return_value = ("Man", "Prod")
            enrich_device_item(
                updater, item, "1-1", False, "", "Original", 2, 3
            )
            updater.update.emit.assert_any_call(item, 2, "Man")
            updater.update.emit.assert_any_call(item, 3, "Man Prod")

            # Test oserror returns early
            mock_read.side_effect = OSError
            enrich_device_item(
                updater, item, "1-1", False, "", "Original", 2, 3
            )

            # Reset side effect
            mock_read.side_effect = None

            # Test generic on windows
            mock_read.return_value = ("Generic", "Prod")
            enrich_device_item(
                updater, item, "1-1", True, "", "Apple iPhone", 2, 3
            )
            updater.update.emit.assert_any_call(item, 2, "Apple")
            updater.update.emit.assert_any_call(item, 3, "Apple iPhone")

            # Test generic on windows with db fallback
            mock_read.return_value = ("Generic", "Prod")
            with patch(
                "usbip_gui.product_detection.product_detection"
                ".get_device_description"
            ) as m_get:
                m_get.return_value = ("DbMfg", "DbProd")
                enrich_device_item(
                    updater,
                    item,
                    "1-1",
                    True,
                    "1234:5678",
                    "Apple iPhone",
                    2,
                    3,
                )
                updater.update.emit.assert_any_call(item, 2, "DbMfg")
                updater.update.emit.assert_any_call(item, 3, "DbProd")


@patch("usbip_gui.product_detection.product_detection.get_device_description")
def test_enrich_remote_device_item(mock_get_db: MagicMock):
    """Test enrich_remote_device_item."""
    mock_get_db.return_value = ("", "")
    item = MagicMock()
    updater = MagicMock()

    def mock_thread_init(*_args: object, **kwargs: object):
        mock_t = MagicMock()
        mock_t.start.side_effect = kwargs["target"]
        return mock_t

    with patch(
        "usbip_gui.product_detection.product_detection.sys.platform", "win32"
    ):
        with patch(
            "usbip_gui.product_detection.product_detection.threading.Thread",
            side_effect=mock_thread_init,
        ):
            with patch(
                "usbip_gui.product_detection.product_detection"
                ".read_windows_registry_usb_descriptor_details"
            ) as mock_read:
                # Test normal
                mock_read.return_value = ("Man", "Prod")
                enrich_remote_device_item(
                    updater, item, "1234:5678", "Original", 2, 3
                )
                updater.update.emit.assert_any_call(item, 2, "Man")
                updater.update.emit.assert_any_call(item, 3, "Prod")

                # Test generic
                mock_read.return_value = ("Generic", "Prod")
                mock_get_db.return_value = ("", "")
                enrich_remote_device_item(
                    updater, item, "1234:5678", "Original", 2, 3
                )
                updater.update.emit.assert_any_call(item, 2, "Original")
                updater.update.emit.assert_any_call(item, 3, "Prod")

                # Test generic with db fallback
                mock_read.return_value = ("Generic", "Prod")
                mock_get_db.return_value = ("DbMfg", "DbProd")
                enrich_remote_device_item(
                    updater, item, "1234:5678", "Original", 2, 3
                )
                updater.update.emit.assert_any_call(item, 2, "DbMfg")
                updater.update.emit.assert_any_call(item, 3, "DbProd")

                # Test empty reg and db fallback empty
                mock_read.return_value = ("", "")
                updater.update.emit.reset_mock()
                with patch(
                    "usbip_gui.product_detection.product_detection"
                    ".get_device_description"
                ) as m_get:
                    m_get.return_value = ("", "")
                    enrich_remote_device_item(
                        updater, item, "1234:5678", "Original", 2, 3
                    )
                    updater.update.emit.assert_not_called()


def test_parse_bus_id():
    """Test parse_bus_id."""
    assert parse_bus_id("1-1.2") == (1, (1, 2))
    assert parse_bus_id("invalid") == (None, ())
    assert parse_bus_id("a-1") == (None, ())  # ValueError branch


def test_matches_device():
    """Test matches_device."""
    mock_dev = MagicMock()
    mock_dev.bus = 1
    mock_dev.port_numbers = (1, 2)

    assert matches_device(mock_dev, "1-1.2")
    assert not matches_device(mock_dev, "2-1")  # bus mismatch

    mock_dev2 = MagicMock()
    mock_dev2.bus = 1
    mock_dev2.port_number = 2
    mock_dev2.port_numbers = None
    assert matches_device(mock_dev2, "1-2")
    assert not matches_device(mock_dev2, "1-3")  # port mismatch


def test_strip_inf_resource():
    """Test _resolve_inf_string."""
    assert (
        _resolve_inf_string("@oem5.inf,%key%;Actual String") == "Actual String"
    )
    assert _resolve_inf_string("Actual String") == "Actual String"


@patch("usbip_gui.product_detection.usb_details.sys.platform", "win32")
def test_get_strings_from_registry():
    """Test get_strings_from_registry."""
    updater = ItemUpdater()
    mock_item = MagicMock(spec=SortableTreeWidgetItem)
    updater.apply_text(mock_item, 1, "test")
    mock_item.setText.assert_called_with(1, "test")
    updater.apply_text(
        object(), 1, "test"
    )  # ignore non SortableTreeWidgetItem

    mock_winreg = MagicMock()
    mock_winreg.OpenKey.return_value = MagicMock()
    mock_winreg.EnumKey.side_effect = ["VID_1234&PID_5678", OSError()]

    def mock_query_value_ex(_k: object, v: str) -> tuple[str, int]:
        if v != "BusReportedDeviceDesc":
            return (f"val_{v}", 1)
        return ("USB desc", 1)

    mock_winreg.QueryValueEx.side_effect = mock_query_value_ex

    sys.modules["winreg"] = mock_winreg
    try:
        _mfg, desc = get_strings_from_registry(0x1234, 0x5678)
        assert desc
    finally:
        del sys.modules["winreg"]


@patch("usbip_gui.product_detection.usb_details.sys")
def test_usb_details_main(mock_sys: MagicMock):
    """Test usb_details main."""
    mock_sys.argv = ["usb_details.py", "1-1"]

    with patch(
        "usbip_gui.product_detection.usb_details.usb.core.find"
    ) as mock_find:
        # Test not found
        mock_find.return_value = None
        main()

        # Test basic found
        mock_dev = MagicMock()
        mock_dev.manufacturer = "Mfg"
        mock_dev.product = "Prd"
        mock_find.return_value = mock_dev
        main()

        # Test ValueError on manufacturer and product
        mock_dev_err = MagicMock()
        type(mock_dev_err).manufacturer = PropertyMock(side_effect=ValueError)
        type(mock_dev_err).product = PropertyMock(side_effect=ValueError)
        mock_find.return_value = mock_dev_err
        main()

        # Test exception on find
        mock_find.side_effect = Exception("Err")
        main()


@patch("usbip_gui.product_detection.product_detection.sys.platform", "linux")
@patch("usbip_gui.product_detection.product_detection.run_elevated")
def test_read_local_usb_descriptor_details_linux(mock_run: MagicMock):
    """Test read_local_usb_descriptor_details on Linux."""
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = json.dumps(
        {"manufacturer": "L_Man", "product": "L_Prod", "error": ""}
    )
    assert read_local_usb_descriptor_details("1-1") == ("L_Man", "L_Prod")

    # Test empty payload
    mock_run.return_value.stdout = ""
    with pytest.raises(OSError):
        read_local_usb_descriptor_details("1-1")

    # Test error in payload
    mock_run.return_value.stdout = json.dumps({"error": "err"})
    with pytest.raises(OSError):
        read_local_usb_descriptor_details("1-1")


@patch("usbip_gui.product_detection.product_detection.sys.platform", "linux")
@patch("usbip_gui.product_detection.product_detection.run_elevated")
def test_read_windows_registry_usb_descriptor_details_linux(
    mock_run: MagicMock,
):
    """Test read_windows_registry_usb_descriptor_details on Linux."""
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = json.dumps(
        {"manufacturer": "L_Man", "product": "L_Prod", "error": ""}
    )
    # read_windows_registry_usb_descriptor_details returns ("", "") on linux
    assert read_windows_registry_usb_descriptor_details("1234:5678") == (
        "",
        "",
    )

    # Test empty payload
    mock_run.return_value.stdout = ""
    assert read_windows_registry_usb_descriptor_details("1-1") == ("", "")

    # Test invalid json
    mock_run.return_value.stdout = "invalid"
    assert read_windows_registry_usb_descriptor_details("1-1") == ("", "")


def test_enrich_device_item_branches():
    """Test enrich_device_item edge cases."""
    item = MagicMock()
    updater = MagicMock()

    def mock_thread_init(*_args: object, **kwargs: object):
        mock_t = MagicMock()
        mock_t.start.side_effect = kwargs["target"]
        return mock_t

    with patch(
        "usbip_gui.product_detection.product_detection.threading.Thread",
        side_effect=mock_thread_init,
    ):
        with patch(
            "usbip_gui.product_detection.product_detection"
            ".read_local_usb_descriptor_details"
        ) as mock_read:
            # Test oserror returns early
            mock_read.side_effect = OSError
            enrich_device_item(
                updater, item, "1-1", False, "", "Original", 2, 3
            )

            # Test generic product fallback to original
            mock_read.side_effect = None
            mock_read.return_value = ("Man", "")
            enrich_device_item(
                updater, item, "1-1", True, "", "DetailedDesc", 2, 3
            )
            updater.update.emit.assert_any_call(item, 3, "DetailedDesc")


@patch("usbip_gui.product_detection.product_detection.get_device_description")
def test_enrich_remote_device_item_branches(mock_get: MagicMock):
    """Test enrich_remote_device_item edge cases."""
    mock_get.return_value = ("", "")
    item = MagicMock()
    updater = MagicMock()

    def mock_thread_init(*_args: object, **kwargs: object):
        mock_t = MagicMock()
        mock_t.start.side_effect = kwargs["target"]
        return mock_t

    with patch(
        "usbip_gui.product_detection.product_detection.sys.platform", "linux"
    ):
        # Returns early if not win32
        enrich_remote_device_item(updater, item, "1234:5678", "Original", 2, 3)

    with patch(
        "usbip_gui.product_detection.product_detection.sys.platform", "win32"
    ):
        with patch(
            "usbip_gui.product_detection.product_detection.threading.Thread",
            side_effect=mock_thread_init,
        ):
            with patch(
                "usbip_gui.product_detection.product_detection"
                ".read_windows_registry_usb_descriptor_details"
            ) as mock_read:
                # Returns early if empty strings
                mock_read.return_value = ("", "")
                enrich_remote_device_item(
                    updater, item, "1234:5678", "Original", 2, 3
                )

                # Test reg_product starts with reg_manufacturer
                mock_read.return_value = ("Man", "ManProd")
                enrich_remote_device_item(
                    updater, item, "1234:5678", "Original", 2, 3
                )
                updater.update.emit.assert_any_call(item, 3, "ManProd")


@patch("usbip_gui.product_detection.usb_details.sys.platform", "linux")
def test_get_strings_from_registry_linux():
    """Test get_strings_from_registry returns early on Linux."""
    assert get_strings_from_registry(0x1234, 0x5678) == ("", "")


def test_main_cli_registry():
    """Test main CLI functionality for registry flags."""
    with patch("usbip_gui.product_detection.usb_details.sys") as mock_sys:
        mock_sys.argv = ["usb_details.py", "1234:5678", "--registry"]
        with patch(
            "usbip_gui.product_detection.usb_details.get_strings_from_registry"
        ) as mock_get:
            mock_get.return_value = ("RM", "RP")
            main()
            mock_get.side_effect = Exception("Err")
            main()


@patch("sys.platform", "win32")
def test_read_windows_registry_usb_descriptor_details_extra():
    """Test read_windows_registry_usb_descriptor_details branches."""

    # Test not win32 or invalid vid_pid
    with patch("sys.platform", "linux"):
        assert read_windows_registry_usb_descriptor_details("1234:5678") == (
            "",
            "",
        )
    assert read_windows_registry_usb_descriptor_details("") == ("", "")
    assert read_windows_registry_usb_descriptor_details("invalid") == ("", "")

    with patch(
        "usbip_gui.product_detection.product_detection.subprocess.run"
    ) as m_run:
        m_run.return_value.returncode = 1
        assert read_windows_registry_usb_descriptor_details("1234:5678") == (
            "",
            "",
        )

        m_run.return_value.returncode = 0
        m_run.return_value.stdout = ""
        assert read_windows_registry_usb_descriptor_details("1234:5678") == (
            "",
            "",
        )

        m_run.return_value.stdout = "invalid json"
        assert read_windows_registry_usb_descriptor_details("1234:5678") == (
            "",
            "",
        )

        m_run.return_value.stdout = '{"error": "some error"}'
        assert read_windows_registry_usb_descriptor_details("1234:5678") == (
            "",
            "",
        )

        m_run.return_value.stdout = (
            '{"manufacturer": "TestMfg", "product": "TestProd"}'
        )
        assert read_windows_registry_usb_descriptor_details("1234:5678") == (
            "TestMfg",
            "TestProd",
        )
