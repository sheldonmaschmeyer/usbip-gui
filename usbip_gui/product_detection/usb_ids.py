"""USB ID Database Downloader and Parser."""

import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Tuple
import functools

USB_IDS_URL = "http://www.linux-usb.org/usb.ids"
CACHE_FILE = Path(__file__).parent / "usb.ids"
CACHE_MAX_AGE = 30 * 24 * 60 * 60  # 30 days


def _download_if_needed() -> None:
    """Download usb.ids file if it doesn't exist or is older than 30 days."""
    try:
        if CACHE_FILE.exists():
            age = time.time() - CACHE_FILE.stat().st_mtime
            if age < CACHE_MAX_AGE:
                return

        req = urllib.request.Request(
            USB_IDS_URL, headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read()

        with open(CACHE_FILE, "wb") as f:
            f.write(content)
    except (urllib.error.URLError, OSError):
        pass


@functools.lru_cache(maxsize=1)
def get_usb_database() -> Dict[str, Dict[str, str]]:
    """Get the parsed USB database."""
    _download_if_needed()

    db: Dict[str, Dict[str, str]] = {}
    if not CACHE_FILE.exists():
        return db

    try:
        with open(CACHE_FILE, "r", encoding="utf-8", errors="replace") as f:
            current_vendor = None
            for line in f:
                if line.startswith("#") or not line.strip():
                    continue

                if not line.startswith("\t"):
                    parts = line.strip().split("  ", 1)
                    if len(parts) == 2:
                        vid = parts[0].strip().lower()
                        vendor_name = parts[1].strip()
                        current_vendor = vid
                        db[current_vendor] = {"__vendor_name__": vendor_name}
                elif line.startswith("\t") and not line.startswith("\t\t"):
                    if current_vendor:
                        parts = line.strip().split("  ", 1)
                        if len(parts) == 2:
                            pid = parts[0].strip().lower()
                            product_name = parts[1].strip()
                            db[current_vendor][pid] = product_name
    except OSError:
        pass

    return db


def get_device_description(vid_pid: str) -> Tuple[str, str]:
    """Get manufacturer and product description given 'VID:PID'."""
    if not vid_pid or ":" not in vid_pid:
        return "", ""

    vid, pid = vid_pid.lower().split(":")
    db = get_usb_database()

    if vid in db:
        vendor_name = db[vid].get("__vendor_name__", "")
        product_name = db[vid].get(pid, "")
        return vendor_name, product_name

    return "", ""
