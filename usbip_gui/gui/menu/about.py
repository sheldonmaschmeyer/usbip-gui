"""About dialog and application information."""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QDialogButtonBox,
    QWidget,
)
from PyQt6.QtCore import Qt
from ..common import VERSION, get_translator
from ...typings import connect_signal

t = get_translator("menu")


def show_about_dialog(parent: QWidget | None = None):
    """Show about dialog."""
    about_text = (
        f"{t('Version')} {VERSION}\n\n"
        f"{t('Original Author')}: K-Francis-H\n"
        f"{t('Fork Maintainer')}: Sheldon Maschmeyer\n\n"
        f"{t('Powered by PyQt6 and USB/IP')}\n"
        f"PyQt6: https://doc.qt.io/qtforpython-6/licenses.html\n"
        f"USB/IP: https://github.com/torvalds/linux/blob/master/"
        f"tools/usb/usbip/README\n"
        f"{t('USB/IP Project')}: https://usbip.sourceforge.net/\n\n"
        f"GitHub: https://github.com/sheldonmaschmeyer/usbip-gui\n\n"
    )

    dialog = QDialog(parent)
    dialog.setWindowTitle(t("About") + " " + t("USB/IP Manager"))

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(20, 20, 20, 20)

    label = QLabel(about_text)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    layout.addWidget(label)

    button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
    connect_signal(button_box.accepted, dialog.accept)
    layout.addWidget(button_box)

    dialog.exec()
