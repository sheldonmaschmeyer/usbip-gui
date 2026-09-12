"""Site configuration persistence, signals, and management."""

from typing import Dict, List, Optional
from PyQt6.QtCore import QObject, pyqtSignal

from .common import load_config, save_config, JsonValue
from .crypto import (
    DecryptionError,
    SECRET_FIELDS,
    SENTINEL_CONFIG_KEY,
    create_sentinel,
    decrypt_field,
    encrypt_field,
    is_encrypted_field,
    master_key_manager,
    verify_sentinel,
)

SiteDict = Dict[str, JsonValue]


class _SitesUpdatedState(QObject):
    """QObject wrapper so site configuration changes emit a Qt signal."""

    changed = pyqtSignal(str)


sites_updated = _SitesUpdatedState()


def _get_key(site_type: str) -> str:
    """Return the configuration key for the given site type."""
    return "client_sites" if site_type == "client" else "server_sites"


def _get_selected_key(site_type: str) -> str:
    """Return the selected site configuration key for the given site type."""
    return (
        "selected_client_site"
        if site_type == "client"
        else "selected_server_site"
    )


def _decrypt_site_secrets(site: SiteDict, key: bytes) -> None:
    """Decrypt any encrypted secret fields in site data."""
    for field in SECRET_FIELDS:
        val = site.get(field)
        if is_encrypted_field(val):
            try:
                site[field] = decrypt_field(val, key)
            except DecryptionError:
                site[field] = ""


def load_sites(site_type: str, decrypt: bool = True) -> List[SiteDict]:
    """
    Load all saved sites for the specified site type ('client' or 'server').

    Args:
        site_type: 'client' or 'server'.
        decrypt: Whether to decrypt secret fields if master key is available.

    Returns:
        List[SiteDict]: List of site configurations.
    """
    config = load_config()
    raw_sites = config.get(_get_key(site_type), [])
    if not isinstance(raw_sites, list):
        return []

    key = master_key_manager.get_key() if decrypt else None
    sites: List[SiteDict] = []
    for item in raw_sites:
        if not isinstance(item, dict):
            continue
        site_copy = dict(item)
        if key is not None:
            _decrypt_site_secrets(site_copy, key)
        sites.append(site_copy)
    return sites


def save_site(site_type: str, site_data: SiteDict) -> None:
    """
    Save or update a single site configuration.

    Args:
        site_type (str): 'client' or 'server'.
        site_data (SiteDict): The site configuration data.
    """
    name = str(site_data.get("name", "")).strip()
    if not name:
        return

    config = load_config()
    key = _get_key(site_type)
    raw_sites = config.get(key, [])
    sites: List[Dict[str, JsonValue]] = (
        [dict(s) for s in raw_sites if isinstance(s, dict)]
        if isinstance(raw_sites, list)
        else []
    )

    sec_key = (
        master_key_manager.get_key()
        if is_master_password_configured() and master_key_manager.is_unlocked()
        else None
    )

    clean_data: Dict[str, JsonValue] = dict(site_data)
    if sec_key is not None:
        for field in SECRET_FIELDS:
            val = clean_data.get(field)
            if isinstance(val, str) and val:
                clean_data[field] = encrypt_field(val, sec_key)

    updated = False
    for idx, existing in enumerate(sites):
        if existing.get("name") == name:
            sites[idx] = clean_data
            updated = True
            break

    if not updated:
        sites.append(clean_data)

    config[key] = sites  # type: ignore[assignment]
    save_config(config)
    sites_updated.changed.emit(site_type)


def save_all_sites(site_type: str, sites: List[SiteDict]) -> None:
    """
    Replace all sites for the specified site type.

    Args:
        site_type (str): 'client' or 'server'.
        sites (List[SiteDict]): Full list of site configurations.
    """
    config = load_config()
    key = _get_key(site_type)
    cleaned: List[Dict[str, JsonValue]] = []
    sec_key = (
        master_key_manager.get_key()
        if is_master_password_configured() and master_key_manager.is_unlocked()
        else None
    )

    for s in sites:
        item: Dict[str, JsonValue] = dict(s)
        if sec_key is not None:
            for field in SECRET_FIELDS:
                val = item.get(field)
                if isinstance(val, str) and val:
                    item[field] = encrypt_field(val, sec_key)
        cleaned.append(item)

    config[key] = cleaned  # type: ignore[assignment]
    save_config(config)
    sites_updated.changed.emit(site_type)


def delete_site(site_type: str, name: str) -> None:
    """
    Delete a site by name.

    Args:
        site_type (str): 'client' or 'server'.
        name (str): The name of the site to remove.
    """
    config = load_config()
    key = _get_key(site_type)
    raw_sites = config.get(key, [])
    if not isinstance(raw_sites, list):
        return

    sites = [
        dict(s)
        for s in raw_sites
        if isinstance(s, dict) and s.get("name") != name
    ]
    config[key] = sites  # type: ignore[assignment]

    sel_key = _get_selected_key(site_type)
    if config.get(sel_key) == name:
        config[sel_key] = ""

    save_config(config)
    sites_updated.changed.emit(site_type)


def get_site(site_type: str, name: str) -> Optional[SiteDict]:
    """
    Retrieve a single site configuration by name.

    Args:
        site_type (str): 'client' or 'server'.
        name (str): The name of the site.

    Returns:
        Optional[SiteDict]: Site data dictionary or None if not found.
    """
    sites = load_sites(site_type)
    for site in sites:
        if site.get("name") == name:
            return dict(site)
    return None


def get_selected_site_name(site_type: str) -> str:
    """
    Get the name of the currently selected site.

    Args:
        site_type (str): 'client' or 'server'.

    Returns:
        str: Name of the selected site, or empty string.
    """
    config = load_config()
    val = config.get(_get_selected_key(site_type), "")
    return str(val) if isinstance(val, str) else ""


def set_selected_site_name(site_type: str, name: str) -> None:
    """
    Set and persist the selected site name.

    Args:
        site_type (str): 'client' or 'server'.
        name (str): Site name to select.
    """
    config = load_config()
    config[_get_selected_key(site_type)] = name
    save_config(config)


def is_master_password_configured() -> bool:
    """Return True if a master password has been configured."""
    config = load_config()
    sentinel = config.get(SENTINEL_CONFIG_KEY)
    return isinstance(sentinel, dict) and sentinel.get("enc") == "v1"


def is_master_password_unlocked() -> bool:
    """Return True if master password is configured and unlocked in RAM."""
    return is_master_password_configured() and master_key_manager.is_unlocked()


def unlock_master_password(password: str) -> bool:
    """
    Verify master password and store key in memory for this session.

    Args:
        password: User-entered password.

    Returns:
        bool: True if verified and unlocked, False otherwise.
    """
    config = load_config()
    sentinel = config.get(SENTINEL_CONFIG_KEY)
    if not isinstance(sentinel, dict):
        return False
    key = verify_sentinel(password, sentinel)
    if key is None:
        return False
    master_key_manager.set_key(key)
    sites_updated.changed.emit("client")
    sites_updated.changed.emit("server")
    return True


def lock_master_password() -> None:
    """Lock the session key cache."""
    master_key_manager.clear()
    sites_updated.changed.emit("client")
    sites_updated.changed.emit("server")


def site_requires_unlock(site: Optional[SiteDict]) -> bool:
    """Return True if site contains encrypted fields and session is locked."""
    if site is None or master_key_manager.is_unlocked():
        return False
    for field in SECRET_FIELDS:
        if is_encrypted_field(site.get(field)):
            return True
    return False


def set_master_password(password: str) -> None:
    """
    Configure a new master password and encrypt all existing site secrets.

    Args:
        password: New master password.
    """
    config = load_config()
    key, sentinel = create_sentinel(password)
    master_key_manager.set_key(key)
    config[SENTINEL_CONFIG_KEY] = sentinel
    save_config(config)

    for st in ("client", "server"):
        current = load_sites(st, decrypt=True)
        save_all_sites(st, current)


def change_master_password(old_password: str, new_password: str) -> bool:
    """
    Change the master password and re-encrypt all site credentials.

    Args:
        old_password: Current master password.
        new_password: New master password.

    Returns:
        bool: True if changed successfully, False if old password invalid.
    """
    config = load_config()
    sentinel = config.get(SENTINEL_CONFIG_KEY)
    if not isinstance(sentinel, dict):
        return False
    old_key = verify_sentinel(old_password, sentinel)
    if old_key is None:
        return False

    master_key_manager.set_key(old_key)
    client_sites = load_sites("client", decrypt=True)
    server_sites = load_sites("server", decrypt=True)

    new_key, new_sentinel = create_sentinel(new_password)
    master_key_manager.set_key(new_key)
    config[SENTINEL_CONFIG_KEY] = new_sentinel
    save_config(config)

    save_all_sites("client", client_sites)
    save_all_sites("server", server_sites)
    return True


def remove_master_password(current_password: str) -> bool:
    """
    Remove master password protection and decrypt credentials to plain text.

    Args:
        current_password: Current master password.

    Returns:
        bool: True if removed successfully, False if password invalid.
    """
    config = load_config()
    sentinel = config.get(SENTINEL_CONFIG_KEY)
    if not isinstance(sentinel, dict):
        return False
    key = verify_sentinel(current_password, sentinel)
    if key is None:
        return False

    master_key_manager.set_key(key)
    client_sites = load_sites("client", decrypt=True)
    server_sites = load_sites("server", decrypt=True)

    config.pop(SENTINEL_CONFIG_KEY, None)
    save_config(config)
    master_key_manager.clear()

    save_all_sites("client", client_sites)
    save_all_sites("server", server_sites)
    return True


def reset_storage() -> None:
    """
    Reset site configuration storage.

    Clears all saved client and server sites, resets selected site names,
    and removes master password protection.
    """
    config = load_config()
    config.pop(SENTINEL_CONFIG_KEY, None)
    config["client_sites"] = []
    config["server_sites"] = []
    config["selected_client_site"] = ""
    config["selected_server_site"] = ""
    master_key_manager.clear()
    save_config(config)
    sites_updated.changed.emit("client")
    sites_updated.changed.emit("server")


def reset_master_password() -> None:
    """Reset master password and clear stored site configuration."""
    reset_storage()
