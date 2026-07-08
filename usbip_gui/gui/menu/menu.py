"""Module for menu.py."""

import tkinter as tk
from tkinter import Menu
from ..common import get_translator
from .about import show_about_dialog
from .language_switcher import toggle_language

_ = get_translator("menu")


def create_main_menu(root: tk.Tk | tk.Toplevel):
    """Docstring for create_main_menu."""
    bg = "#1e1e2e"
    fg = "#cdd6f4"
    abg = "#45475a"
    afg = "#cdd6f4"
    bw = 0

    menubar = Menu(
        root,
        bg=bg,
        fg=fg,
        activebackground=abg,
        activeforeground=afg,
        borderwidth=bw,
    )

    filemenu = Menu(
        menubar,
        tearoff=0,
        bg=bg,
        fg=fg,
        activebackground=abg,
        activeforeground=afg,
        borderwidth=bw,
    )
    filemenu.add_command(
        label=_("About"), command=lambda: show_about_dialog(root)
    )
    filemenu.add_separator()
    filemenu.add_command(label=_("Close"), command=root.quit)

    menubar.add_cascade(label=_("File"), menu=filemenu)

    # Add Language toggle directly to the menu bar
    menubar.add_command(label="EN / FR", command=toggle_language)

    root.config(menu=menubar)
