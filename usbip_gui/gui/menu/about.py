"""About dialog and application information."""

from PyQt6.QtWidgets import QMessageBox, QWidget
from ..common import VERSION, get_translator

t = get_translator("menu")


def show_about_dialog(parent: QWidget | None = None):
    """Show about dialog."""
    about_text = (
        f"{t('Version')} {VERSION}\n\n"
        f"{t('Original Author')}: K-Francis-H\n"
        f"{t('Fork Maintainer')}: Sheldon Maschmeyer\n\n"
        f"GitHub: https://github.com/sheldonmaschmeyer/usbip-gui"
    )

    QMessageBox.about(
        parent, t("About") + " " + t("USB/IP Manager"), about_text
    )
