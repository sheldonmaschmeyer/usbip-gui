"""Language switching utilities."""

from ..common import get_translator, get_current_language, set_language

t = get_translator("menu")


def toggle_language() -> None:
    """Toggle the active language between English and French, in place.

    This updates the shared language state and emits `language_changed`, so
    the running UI can refresh its text immediately without closing and
    reopening the application.
    """
    current_lang = get_current_language()
    new_lang = "fr_CA" if current_lang != "fr_CA" else "en"
    set_language(new_lang)
