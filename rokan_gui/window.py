"""
Rokan GUI Window — NATIVE desktop application.
Uses pywebview + WebKitGTK = real GTK window, NOT a browser.
On Ubuntu: looks and feels like a proper GNOME app.
"""

import os
import sys

PORT = 18991
URL = f"http://127.0.0.1:{PORT}"


def _check_gtk_deps():
    """Check if GTK/WebKit system deps are installed. Guide the user if not."""
    missing = []

    try:
        import gi
    except ImportError:
        missing.append("python3-gi")

    if not missing:
        try:
            gi.require_version("Gtk", "3.0")
            from gi.repository import Gtk
        except (ValueError, ImportError):
            missing.append("gir1.2-gtk-3.0")

        try:
            gi.require_version("WebKit2", "4.1")
            from gi.repository import WebKit2
        except (ValueError, ImportError):
            # Try 4.0 fallback
            try:
                gi.require_version("WebKit2", "4.0")
                from gi.repository import WebKit2
            except (ValueError, ImportError):
                missing.append("gir1.2-webkit2-4.1")

    if missing:
        pkgs = " ".join(missing)
        print(f"\n[ROKAN] Missing system packages for native window: {pkgs}")
        print(f"[ROKAN] Install them:\n")
        print(f"  sudo apt install {pkgs} python3-gi-cairo\n")
        print(f"[ROKAN] Then run 'rokan gui' again.\n")
        sys.exit(1)


def launch():
    """Launch Rokan as a native desktop application. No browser."""
    # Verify deps first
    _check_gtk_deps()

    import webview
    from rokan_gui.server import start_server_thread

    print("[ROKAN] Starting backend...")
    start_server_thread(port=PORT)
    print(f"[ROKAN] Backend ready")

    print("[ROKAN] Opening native window...")

    # Create a REAL native GTK window
    window = webview.create_window(
        title="Rokan",
        url=URL,
        width=1280,
        height=820,
        min_size=(900, 600),
        resizable=True,
        text_select=True,
        zoomable=True,
        background_color="#08080f",
    )

    # Force GTK backend on Linux
    gui_backend = None
    if sys.platform.startswith("linux"):
        gui_backend = "gtk"

    webview.start(
        gui=gui_backend,
        debug="--debug" in sys.argv,
    )

    print("[ROKAN] Shutdown.")


if __name__ == "__main__":
    launch()
