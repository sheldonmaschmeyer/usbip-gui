"""About dialog and application information."""

import tkinter as tk
from tkinter.ttk import Button
from ..common import VERSION, get_translator

t = get_translator("menu")


def show_about_dialog(parent: tk.Tk | tk.Toplevel | None = None):
    """Show about dialog."""
    dialog = tk.Toplevel(parent)
    dialog.title(t("About"))
    dialog.geometry("500x250")
    dialog.configure(bg="#1e1e2e")
    dialog.resizable(False, False)

    if parent:
        dialog.transient(parent)
        dialog.grab_set()

    about_text = (
        f"{t('USB/IP Manager')}\n"
        f"{t('Version')} {VERSION}\n\n"
        f"{t('Original Author')}: K-Francis-H\n"
        f"{t('Fork Maintainer')}: Sheldon Maschmeyer\n\n"
        f"GitHub: https://github.com/sheldonmaschmeyer/usbip-gui"
    )

    label = tk.Label(
        dialog,
        text=about_text,
        bg="#1e1e2e",
        fg="#cdd6f4",
        font=("Ubuntu", 11, "bold"),
        justify="center",
    )
    label.pack(expand=True, padx=20, pady=20)

    btn = Button(dialog, text="OK", command=dialog.destroy)
    btn.pack(pady=(0, 20))
