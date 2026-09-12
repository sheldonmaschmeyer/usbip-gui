"""Unit tests for site_config persistence and signals."""

from unittest.mock import patch
from usbip_gui.common.site_config import (
    load_sites,
    save_site,
    save_all_sites,
    delete_site,
    get_site,
    get_selected_site_name,
    set_selected_site_name,
    sites_updated,
)


def test_load_sites_not_list():
    """Test load_sites returns empty list when config value is not a list."""
    with patch("usbip_gui.common.site_config.load_config") as mock_load:
        mock_load.return_value = {"client_sites": "invalid"}
        assert load_sites("client") == []


def test_load_sites_filters_non_dicts():
    """Test load_sites filters out non-dictionary items."""
    with patch("usbip_gui.common.site_config.load_config") as mock_load:
        mock_load.return_value = {
            "client_sites": [
                "invalid",
                123,
                {"name": "Site1", "connection_type": "direct"},
            ]
        }
        sites = load_sites("client")
        assert len(sites) == 1
        assert sites[0]["name"] == "Site1"


def test_save_site_empty_name():
    """Test save_site ignores site data with empty name."""
    with patch("usbip_gui.common.site_config.load_config") as mock_load:
        with patch("usbip_gui.common.site_config.save_config") as mock_save:
            save_site("client", {"name": "   "})
            mock_load.assert_not_called()
            mock_save.assert_not_called()


def test_save_site_new_and_update():
    """Test save_site adds a new site and updates an existing one."""
    mock_config: dict[str, object] = {"client_sites": "corrupt"}
    with patch(
        "usbip_gui.common.site_config.load_config", return_value=mock_config
    ):
        with patch("usbip_gui.common.site_config.save_config") as mock_save:
            emitted = []
            sites_updated.changed.connect(emitted.append)
            try:
                # Add new site
                save_site(
                    "client",
                    {
                        "name": "Site A",
                        "connection_type": "direct",
                        "remote_ip": "1.2.3.4",
                    },
                )
                assert emitted == ["client"]
                mock_save.assert_called_once()
                sites_list = mock_config["client_sites"]
                assert isinstance(sites_list, list)
                assert len(sites_list) == 1
                assert sites_list[0]["name"] == "Site A"

                # Update existing site
                save_site(
                    "client",
                    {
                        "name": "Site A",
                        "connection_type": "cloudflared",
                        "cloudflared_hostname": "usbip.maschmeyer.ca",
                    },
                )
                updated_sites = mock_config["client_sites"]
                first_site = updated_sites[0]  # type: ignore[index]
                assert first_site["connection_type"] == "cloudflared"
            finally:
                sites_updated.changed.disconnect(emitted.append)


def test_save_all_sites():
    """Test save_all_sites replaces all sites."""
    mock_config: dict[str, object] = {}
    with patch(
        "usbip_gui.common.site_config.load_config", return_value=mock_config
    ):
        with patch("usbip_gui.common.site_config.save_config") as mock_save:
            emitted = []
            sites_updated.changed.connect(emitted.append)
            try:
                save_all_sites(
                    "server",
                    [
                        {"name": "S1", "connection_type": "direct"},
                        {"name": "S2", "connection_type": "cloudflared"},
                    ],
                )
                mock_save.assert_called_once()
                assert emitted == ["server"]
                assert len(mock_config["server_sites"]) == 2  # pyright: ignore
            finally:
                sites_updated.changed.disconnect(emitted.append)


def test_delete_site_not_list():
    """Test delete_site returns early if config raw_sites is not a list."""
    with patch("usbip_gui.common.site_config.load_config") as mock_load:
        mock_load.return_value = {"client_sites": 123}
        with patch("usbip_gui.common.site_config.save_config") as mock_save:
            delete_site("client", "Site1")
            mock_save.assert_not_called()


def test_delete_site_success_and_reset_selected():
    """Test delete_site removes site and resets selected site if matched."""
    mock_config: dict[str, object] = {
        "client_sites": [
            {"name": "Site1"},
            {"name": "Site2"},
            "invalid_entry",
        ],
        "selected_client_site": "Site1",
    }
    with patch(
        "usbip_gui.common.site_config.load_config", return_value=mock_config
    ):
        with patch("usbip_gui.common.site_config.save_config") as mock_save:
            emitted = []
            sites_updated.changed.connect(emitted.append)
            try:
                delete_site("client", "Site1")
                mock_save.assert_called_once()
                assert emitted == ["client"]
                assert mock_config["selected_client_site"] == ""
                remaining = mock_config["client_sites"]
                assert isinstance(remaining, list)
                assert len(remaining) == 1
                assert remaining[0]["name"] == "Site2"

                # Delete another site that is not the selected site
                mock_config["selected_client_site"] = "OtherSite"
                delete_site("client", "Site2")
                assert mock_config["selected_client_site"] == "OtherSite"
            finally:
                sites_updated.changed.disconnect(emitted.append)


def test_get_site_found_and_not_found():
    """Test get_site returns matching site or None."""
    with patch("usbip_gui.common.site_config.load_config") as mock_load:
        mock_load.return_value = {
            "server_sites": [
                {"name": "Server1", "port": 3240},
            ]
        }
        site = get_site("server", "Server1")
        assert site is not None
        assert site["port"] == 3240

        missing = get_site("server", "NonExistent")
        assert missing is None


def test_get_and_set_selected_site_name():
    """Test get_selected_site_name and set_selected_site_name."""
    mock_config: dict[str, object] = {
        "selected_client_site": "MySite",
        "selected_server_site": 123,  # non-str
    }
    with patch(
        "usbip_gui.common.site_config.load_config", return_value=mock_config
    ):
        with patch("usbip_gui.common.site_config.save_config") as mock_save:
            assert get_selected_site_name("client") == "MySite"
            assert get_selected_site_name("server") == ""

            set_selected_site_name("client", "NewSite")
            assert mock_config["selected_client_site"] == "NewSite"
            mock_save.assert_called_once()
