"""Language switching utilities and environment management."""

import os
import sys
from ..common import get_translator

t = get_translator("menu")


def toggle_language():
    """Toggle language."""
    current_lang = os.environ.get("LANGUAGE", "en")
    new_lang = "fr_CA" if current_lang != "fr_CA" else "en"
    os.environ["LANGUAGE"] = new_lang
    os.execv(sys.executable, [sys.executable] + sys.argv)
