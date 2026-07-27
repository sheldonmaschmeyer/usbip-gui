"""Tests for the usb_ids database downloader and parser."""

import time
from unittest.mock import MagicMock, mock_open, patch

from usbip_gui.product_detection import usb_ids
from usbip_gui.product_detection.usb_ids import (
    _download_if_needed,  # pyright: ignore[reportPrivateUsage]
    get_device_description,
    get_usb_database,
)


def test_download_if_needed_cache_fresh():
    """Test downloading skipped when cache is fresh."""
    with patch("pathlib.Path.exists") as m_exists:
        with patch("pathlib.Path.stat") as m_stat:
            m_exists.return_value = True
            m_stat.return_value.st_mtime = time.time() - 1000  # Fresh

            with patch(
                "usbip_gui.product_detection.usb_ids.urllib.request.urlopen"
            ) as m_urlopen:
                _download_if_needed()
                m_urlopen.assert_not_called()


def test_download_if_needed_cache_old():
    """Test downloading triggers when cache is old."""
    with patch("pathlib.Path.exists") as m_exists:
        with patch("pathlib.Path.stat") as m_stat:
            m_exists.return_value = True
            m_stat.return_value.st_mtime = (
                time.time() - 40 * 24 * 60 * 60
            )  # Older than 30 days

            with patch(
                "usbip_gui.product_detection.usb_ids.urllib.request.urlopen"
            ) as m_urlopen:
                m_ctx = m_urlopen.return_value.__enter__.return_value
                m_ctx.read.return_value = b"test"
                with patch(
                    "usbip_gui.product_detection.usb_ids.open", mock_open()
                ) as m_open:
                    _download_if_needed()
                    m_urlopen.assert_called_once()
                    m_open.assert_called_once()


def test_download_if_needed_exception():
    """Test downloading gracefully handles exceptions."""
    with patch("pathlib.Path.exists") as m_exists:
        m_exists.return_value = False
        with patch(
            "usbip_gui.product_detection.usb_ids.urllib.request.urlopen",
            side_effect=OSError("Failed"),
        ):
            # Should not raise
            _download_if_needed()


def test_get_usb_database_empty_without_file():
    """Test getting DB when file does not exist after download attempt."""
    # Reset cache
    usb_ids.get_usb_database.cache_clear()

    with patch("usbip_gui.product_detection.usb_ids._download_if_needed"):
        with patch("pathlib.Path.exists", return_value=False):
            db = get_usb_database()
            assert not db


def test_get_usb_database_with_file():
    """Test parsing the usb.ids file."""
    # Reset cache
    usb_ids.get_usb_database.cache_clear()

    mock_db_content = (
        "# Some comment\n"
        "\n"
        "1234  Vendor Name\n"
        "\t5678  Product Name\n"
        "\tabcd  Another Product\n"
        "\t\t01  Interface\n"
        "9999  Other Vendor\n"
    )

    with patch("usbip_gui.product_detection.usb_ids._download_if_needed"):
        with patch("pathlib.Path.exists", return_value=True):
            with patch(
                "usbip_gui.product_detection.usb_ids.open",
                mock_open(read_data=mock_db_content),
            ):
                db = get_usb_database()
                assert "1234" in db
                assert db["1234"]["__vendor_name__"] == "Vendor Name"
                assert db["1234"]["5678"] == "Product Name"
                assert db["1234"]["abcd"] == "Another Product"
                assert "9999" in db
                assert db["9999"]["__vendor_name__"] == "Other Vendor"


def test_get_usb_database_exception():
    """Test parsing gracefully handles exceptions."""
    usb_ids.get_usb_database.cache_clear()
    with patch("usbip_gui.product_detection.usb_ids._download_if_needed"):
        with patch("pathlib.Path.exists", return_value=True):
            with patch(
                "usbip_gui.product_detection.usb_ids.open",
                side_effect=OSError("Read error"),
            ):
                db = get_usb_database()
                assert not db


@patch("usbip_gui.product_detection.usb_ids.get_usb_database")
def test_get_device_description(mock_db: MagicMock):
    """Test get_device_description lookups."""
    # Populate cache directly for testing
    mock_db.return_value = {
        "1234": {"__vendor_name__": "Mock Vendor", "5678": "Mock Product"}
    }

    # Test valid lookup
    mfg, prod = get_device_description("1234:5678")
    assert mfg == "Mock Vendor"
    assert prod == "Mock Product"

    # Test valid vendor, missing product
    mfg, prod = get_device_description("1234:9999")
    assert mfg == "Mock Vendor"
    assert prod == ""

    # Test missing vendor
    mfg, prod = get_device_description("abcd:ef01")
    assert mfg == ""
    assert prod == ""

    # Test invalid format
    mfg, prod = get_device_description("invalid")
    assert mfg == ""
    assert prod == ""

    mfg, prod = get_device_description("")
    assert mfg == ""
    assert prod == ""
