"""Unit tests for site_config persistence and signals."""

# pylint: disable=invalid-sequence-index

from typing import cast
from unittest.mock import patch
from usbip_gui.common.crypto import (
    create_sentinel,
    master_key_manager,
)
from usbip_gui.common.site_config import (
    SiteDict,
    change_master_password,
    delete_site,
    get_selected_site_name,
    get_site,
    is_master_password_configured,
    is_master_password_unlocked,
    load_sites,
    lock_master_password,
    remove_master_password,
    reset_master_password,
    reset_storage,
    save_all_sites,
    save_site,
    set_master_password,
    set_selected_site_name,
    site_requires_unlock,
    unlock_master_password,
)


class _SignalRecorder:
    """Capture emitted site-update events without patching Qt signals."""

    def __init__(self) -> None:
        self.emitted: list[str] = []

    def emit(self, site_type: str) -> None:
        """Record a signal emission."""
        self.emitted.append(site_type)


class _SitesUpdatedStub:
    """Minimal sites_updated replacement for persistence tests."""

    def __init__(self) -> None:
        self.changed = _SignalRecorder()


def test_load_sites_not_list():
    """Test load_sites returns empty list when config value is not a list."""
    with patch("usbip_gui.common.site_config.load_config") as mock_load:
        mock_load.return_value = {"client_sites": "invalid"}
        assert not load_sites("client")


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
            sites_updated_stub = _SitesUpdatedStub()
            with patch(
                "usbip_gui.common.site_config.sites_updated",
                sites_updated_stub,
            ):
                # Add new site
                save_site(
                    "client",
                    {
                        "name": "Site A",
                        "connection_type": "direct",
                        "remote_ip": "1.2.3.4",
                    },
                )
                assert sites_updated_stub.changed.emitted == ["client"]
                mock_save.assert_called_once()
                sites_list = mock_config["client_sites"]
                assert isinstance(sites_list, list)
                typed_sites = cast(list[dict[str, object]], sites_list)
                assert len(typed_sites) == 1
                assert typed_sites[0]["name"] == "Site A"

                # Update existing site
                sites_updated_stub.changed.emitted.clear()
                save_site(
                    "client",
                    {
                        "name": "Site A",
                        "connection_type": "cloudflared",
                        "cloudflared_hostname": "usbip.maschmeyer.ca",
                    },
                )
                assert sites_updated_stub.changed.emitted == ["client"]
                updated_sites = mock_config["client_sites"]
                assert isinstance(updated_sites, list)
                first_site = cast(dict[str, object], updated_sites[0])
                assert first_site["connection_type"] == "cloudflared"


def test_save_all_sites():
    """Test save_all_sites replaces all sites."""
    mock_config: dict[str, object] = {}
    with patch(
        "usbip_gui.common.site_config.load_config", return_value=mock_config
    ):
        with patch("usbip_gui.common.site_config.save_config") as mock_save:
            sites_updated_stub = _SitesUpdatedStub()
            with patch(
                "usbip_gui.common.site_config.sites_updated",
                sites_updated_stub,
            ):
                save_all_sites(
                    "server",
                    [
                        {"name": "S1", "connection_type": "direct"},
                        {"name": "S2", "connection_type": "cloudflared"},
                    ],
                )
                mock_save.assert_called_once()
                assert sites_updated_stub.changed.emitted == ["server"]
                saved_sites = cast(
                    list[dict[str, object]], mock_config["server_sites"]
                )
                assert len(saved_sites) == 2


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
            sites_updated_stub = _SitesUpdatedStub()
            with patch(
                "usbip_gui.common.site_config.sites_updated",
                sites_updated_stub,
            ):
                delete_site("client", "Site1")
                mock_save.assert_called_once()
                assert sites_updated_stub.changed.emitted == ["client"]
                assert mock_config["selected_client_site"] == ""
                remaining = cast(
                    list[dict[str, object]], mock_config["client_sites"]
                )
                assert len(remaining) == 1
                assert remaining[0]["name"] == "Site2"

                # Delete another site that is not the selected site
                sites_updated_stub.changed.emitted.clear()
                mock_config["selected_client_site"] = "OtherSite"
                delete_site("client", "Site2")
                assert sites_updated_stub.changed.emitted == ["client"]
                assert mock_config["selected_client_site"] == "OtherSite"


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


def test_master_password_configured_and_unlocked():
    """Test is_master_password_configured and is_master_password_unlocked."""
    # No sentinel in config
    with patch("usbip_gui.common.site_config.load_config", return_value={}):
        assert not is_master_password_configured()
        assert not is_master_password_unlocked()

    # Invalid sentinel
    with patch(
        "usbip_gui.common.site_config.load_config",
        return_value={"master_password_sentinel": "invalid"},
    ):
        assert not is_master_password_configured()

    # Valid sentinel present
    fake_sentinel = {"enc": "v1", "salt": "abc", "ciphertext": "xyz"}
    with patch(
        "usbip_gui.common.site_config.load_config",
        return_value={"master_password_sentinel": fake_sentinel},
    ):
        assert is_master_password_configured()
        master_key_manager.clear()
        assert not is_master_password_unlocked()

        master_key_manager.set_key(b"k" * 32)
        assert is_master_password_unlocked()

        lock_master_password()
        assert not is_master_password_unlocked()


def test_unlock_master_password():
    """Test unlock_master_password."""
    key, sentinel = create_sentinel("testpass", iterations=1000)
    mock_config = {"master_password_sentinel": sentinel}

    with patch(
        "usbip_gui.common.site_config.load_config", return_value=mock_config
    ):
        # No sentinel case
        with patch(
            "usbip_gui.common.site_config.load_config", return_value={}
        ):
            assert not unlock_master_password("testpass")

        # Wrong password
        assert not unlock_master_password("wrong")
        assert not master_key_manager.is_unlocked()

        # Correct password
        assert unlock_master_password("testpass")
        assert master_key_manager.is_unlocked()
        assert master_key_manager.get_key() == key
        master_key_manager.clear()


def test_site_requires_unlock():
    """Test site_requires_unlock helper."""
    master_key_manager.clear()
    assert not site_requires_unlock(None)
    assert not site_requires_unlock({"name": "Site1", "password": "plain"})

    encrypted_site: SiteDict = {
        "name": "Site2",
        "password": {"enc": "v1", "nonce": "a", "ciphertext": "b"},
    }
    assert site_requires_unlock(encrypted_site)

    # When unlocked, requires_unlock is False
    master_key_manager.set_key(b"k" * 32)
    assert not site_requires_unlock(encrypted_site)
    master_key_manager.clear()


def test_set_change_remove_and_reset_master_password():
    """Test full master password lifecycle."""
    mock_config: dict[str, object] = {
        "client_sites": [
            {
                "name": "Client1",
                "password": "secret_pwd",
                "cloudflared_token_secret": "my_secret",
            }
        ],
        "server_sites": [
            {
                "name": "Server1",
                "cloudflared_token": "cf_tunnel_token",
            }
        ],
    }

    with patch(
        "usbip_gui.common.site_config.load_config", return_value=mock_config
    ):
        with patch("usbip_gui.common.site_config.save_config"):

            def fake_create_sentinel(pw: str) -> tuple[bytes, dict[str, str]]:
                return (
                    b"k" * 32,
                    {"enc": "v1", "salt": "s", "ciphertext": pw},
                )

            def fake_verify_sentinel(
                pw: str, sentinel: dict[str, object]
            ) -> bytes | None:
                ciphertext = sentinel.get("ciphertext")
                return b"k" * 32 if pw == ciphertext else None

            with patch(
                "usbip_gui.common.site_config.create_sentinel",
                side_effect=fake_create_sentinel,
            ):
                with patch(
                    "usbip_gui.common.site_config.verify_sentinel",
                    side_effect=fake_verify_sentinel,
                ):
                    # 1. Set master password
                    set_master_password("pass1")
                    assert "master_password_sentinel" in mock_config
                    assert master_key_manager.is_unlocked()

                    # Sites should be encrypted
                    c_sites = mock_config["client_sites"]
                    assert isinstance(c_sites, list)
                    assert isinstance(c_sites[0]["password"], dict)

                    # 2. Change master password - invalid old password
                    assert not change_master_password("wrong", "pass2")

                    # 2b. Change master password - valid old password
                    assert change_master_password("pass1", "pass2")
                    sentinel = mock_config["master_password_sentinel"]
                    assert isinstance(sentinel, dict)
                    assert sentinel["ciphertext"] == "pass2"

                    # 3. Remove master password - invalid current password
                    assert not remove_master_password("wrong")

                    # 3b. Remove master password - valid current password
                    assert remove_master_password("pass2")
                    assert "master_password_sentinel" not in mock_config
                    assert not master_key_manager.is_unlocked()

                    # Secrets are plain text again
                    c_sites = mock_config["client_sites"]
                    assert isinstance(c_sites, list)
                    typed_c = cast(list[dict[str, object]], c_sites)
                    assert isinstance(typed_c[0]["password"], str)

                    # 4. Set password again, then test reset
                    set_master_password("pass3")
                    reset_master_password()
                    assert "master_password_sentinel" not in mock_config
                    assert not master_key_manager.is_unlocked()
                    c_sites = mock_config["client_sites"]
                    assert isinstance(c_sites, list)
                    assert not c_sites


def test_change_and_remove_without_sentinel():
    """Test change and remove when sentinel is missing."""

    with patch("usbip_gui.common.site_config.load_config", return_value={}):
        assert not change_master_password("old", "new")
        assert not remove_master_password("old")


def test_load_sites_decryption_error():
    """Test load_sites handles DecryptionError cleanly."""
    master_key_manager.set_key(b"k" * 32)
    mock_config: dict[str, object] = {
        "client_sites": [
            {
                "name": "Site1",
                "password": {"enc": "v1", "nonce": "bad", "ciphertext": "bad"},
            }
        ]
    }
    with patch(
        "usbip_gui.common.site_config.load_config", return_value=mock_config
    ):
        sites = load_sites("client", decrypt=True)
        assert len(sites) == 1
        assert sites[0]["password"] == ""

    master_key_manager.clear()


def test_save_all_sites_with_master_password_unlocked():
    """Test save_all_sites encrypts secret fields when master key is active."""
    master_key_manager.set_key(b"k" * 32)
    mock_config: dict[str, object] = {
        "master_password_sentinel": {"enc": "v1"},
        "client_sites": [],
    }
    with patch(
        "usbip_gui.common.site_config.load_config", return_value=mock_config
    ):
        with patch("usbip_gui.common.site_config.save_config"):
            save_all_sites(
                "client",
                [
                    {
                        "name": "SecureSite",
                        "password": "mypassword",
                        "cloudflared_token_id": "id1",
                        "cloudflared_token_secret": "sec1",
                    }
                ],
            )
            saved_sites = cast(
                list[dict[str, object]], mock_config["client_sites"]
            )
            assert len(saved_sites) == 1
            first_site = saved_sites[0]
            assert isinstance(first_site["password"], dict)

    master_key_manager.clear()


def test_save_site_with_master_password_unlocked():
    """Test save_site encrypts secret fields when master key is active."""
    master_key_manager.set_key(b"k" * 32)
    mock_config: dict[str, object] = {
        "master_password_sentinel": {"enc": "v1"},
        "client_sites": [],
    }
    with patch(
        "usbip_gui.common.site_config.load_config", return_value=mock_config
    ):
        with patch("usbip_gui.common.site_config.save_config"):
            save_site(
                "client",
                {
                    "name": "SecureSite",
                    "password": "mypassword",
                    "cloudflared_token_id": "id1",
                    "cloudflared_token_secret": "sec1",
                },
            )
            saved_sites = cast(
                list[dict[str, object]], mock_config["client_sites"]
            )
            assert len(saved_sites) == 1
            first_site = saved_sites[0]
            assert isinstance(first_site["password"], dict)

    master_key_manager.clear()


def test_reset_storage():
    """Test reset_storage clears sites, selection, and sentinel."""
    master_key_manager.set_key(b"k" * 32)
    mock_config = {
        "master_password_sentinel": {"enc": "v1"},
        "client_sites": [{"name": "Site1"}],
        "server_sites": [{"name": "Site2"}],
        "selected_client_site": "Site1",
        "selected_server_site": "Site2",
    }
    with patch(
        "usbip_gui.common.site_config.load_config", return_value=mock_config
    ):
        with patch("usbip_gui.common.site_config.save_config"):
            reset_storage()
            assert "master_password_sentinel" not in mock_config
            assert not mock_config["client_sites"]
            assert not mock_config["server_sites"]
            assert mock_config["selected_client_site"] == ""
            assert mock_config["selected_server_site"] == ""
            assert not master_key_manager.is_unlocked()
