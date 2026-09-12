"""Site configuration persistence, signals, and management."""

from typing import Dict, List, Optional
from PyQt6.QtCore import QObject, pyqtSignal

from .common import load_config, save_config, JsonValue

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


def load_sites(site_type: str) -> List[SiteDict]:
    """
    Load all saved sites for the specified site type ('client' or 'server').

    Returns:
        List[SiteDict]: List of site configurations.
    """
    config = load_config()
    raw_sites = config.get(_get_key(site_type), [])
    if not isinstance(raw_sites, list):
        return []

    sites: List[SiteDict] = []
    for item in raw_sites:
        if isinstance(item, dict):
            sites.append(dict(item))
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

    updated = False
    clean_data: Dict[str, JsonValue] = dict(site_data)
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
    cleaned: List[Dict[str, JsonValue]] = [dict(s) for s in sites]
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
