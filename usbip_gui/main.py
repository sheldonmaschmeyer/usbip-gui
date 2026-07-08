"""Main entry point for the USB/IP GUI application."""

import sys
import os

# Ensure the root project directory is on sys.path so 'usbip_gui' is
# discoverable even if this script is executed directly via its file path (e.g.
# during language switch)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if __name__ == "__main__":
    from usbip_gui.gui import start_app

    start_app()
