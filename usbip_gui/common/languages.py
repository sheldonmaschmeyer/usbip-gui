"""Language detection, switching, and JSON translation helpers."""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Tuple, Callable

from babel.core import Locale
from PyQt6.QtCore import QObject, pyqtSignal

from .common import load_config, save_config


class _LanguageState(QObject):
    """QObject wrapper so plain functions/modules can emit a Qt signal."""

    changed = pyqtSignal(str)

    def __init__(self) -> None:
        """Initialize the class instance."""
        super().__init__()
        self.current: Optional[str] = None


language_changed = _LanguageState()


def _detect_system_language() -> str:
    """Detect the system default language using Babel."""
    lang = "en"
    try:
        loc = Locale.default()
        if loc and loc.language:
            lang = loc.language
            if loc.territory:
                lang = f"{loc.language}_{loc.territory}"
    except Exception:  # pylint: disable=broad-exception-caught
        # Babel can raise TypeError when environment variables are present but
        # empty. Fall back to English if locale can't be determined.
        pass
    return lang


def get_current_language() -> str:
    """Get the active UI language."""
    if language_changed.current is None:
        saved = load_config().get("language")
        language_changed.current = (
            saved
            if isinstance(saved, str) and saved
            else _detect_system_language()
        )
    return language_changed.current


def set_language(lang: str) -> None:
    """
    Set the active UI language and notify listeners so the UI can refresh.
    """
    language_changed.current = lang
    os.environ["LANGUAGE"] = lang
    config = load_config()
    config["language"] = lang
    save_config(config)
    language_changed.changed.emit(lang)


def get_translator(domain: str) -> Callable[[str], str]:
    """Get translator loading from JSON files to avoid compiling .mo files."""
    locales_dir = Path(__file__).parent.parent / "locales"
    cache: Dict[str, Tuple[Dict[str, str], Dict[str, str]]] = {}

    def load_json(name: str, language_code: str) -> Dict[str, str]:
        base_lang = language_code.split("_")[0]
        path = locales_dir / base_lang / f"{name}.json"
        if not path.exists():
            path = locales_dir / "en" / f"{name}.json"

        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError):
                pass
        return {}

    def translate(message: str) -> str:
        lang = get_current_language()
        cached = cache.get(lang)
        if cached is None:
            common_translations = load_json("common", lang)
            domain_translations = (
                load_json(domain, lang) if domain != "common" else {}
            )
            cached = (common_translations, domain_translations)
            cache[lang] = cached
        common_translations, domain_translations = cached
        if message in domain_translations and domain_translations[message]:
            return domain_translations[message]
        if message in common_translations and common_translations[message]:
            return common_translations[message]
        return message

    return translate


t = get_translator("common")
