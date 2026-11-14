"""Read/write the local OS clipboard.

pyperclip handles the per-platform ugliness for us: ctypes Win32 on
Windows (no PowerShell startup), pbcopy/pbpaste on macOS, GPaste D-Bus
on GNOME-Wayland, and xclip/xsel/wl-clipboard fallback elsewhere.

`available()` is meant to be called once at startup so we can disable
clipboard sync cleanly + log an actionable hint instead of warning on
every poll cycle. On Linux without xclip/wl-clipboard installed,
pyperclip raises `PyperclipException`; we treat that as "no clipboard"
and silently no-op the rest of the session.
"""
from __future__ import annotations

import logging
import os
import sys
from typing import Optional

import pyperclip


log = logging.getLogger(__name__)


def _kde_wayland() -> bool:
    desktops = os.environ.get("XDG_CURRENT_DESKTOP", "").upper().split(":")
    return sys.platform.startswith("linux") and bool(os.environ.get("WAYLAND_DISPLAY")) and "KDE" in desktops


def _klipper():
    import dbus
    bus = dbus.SessionBus()
    return dbus.Interface(bus.get_object("org.kde.klipper", "/klipper"), "org.kde.klipper.klipper")


def available() -> bool:
    """Probe the platform clipboard. True if reads/writes will work.

    Logs a one-line install hint on Linux when no helper is on PATH so
    the user knows what to install."""
    if _kde_wayland():
        try:
            _klipper().getClipboardContents()
            return True
        except Exception as e:
            log.warning("clipboard sync disabled — KDE clipboard service unavailable: %s", e)
            return False
    try:
        pyperclip.paste()
        return True
    except pyperclip.PyperclipException as e:
        if sys.platform.startswith("linux"):
            log.warning(
                "clipboard sync disabled — install a helper: "
                "`apt install xclip` (X11) or `apt install wl-clipboard` "
                "(Wayland). Underlying error: %s", e,
            )
        else:
            log.warning("clipboard sync disabled: %s", e)
        return False


def read_text() -> Optional[str]:
    """Return the current local clipboard text, or None on failure."""
    if _kde_wayland():
        try:
            return str(_klipper().getClipboardContents())
        except Exception as e:
            log.debug("KDE clipboard read failed: %s", e)
            return None
    try:
        return pyperclip.paste()
    except pyperclip.PyperclipException:
        return None


def push_text(text: str) -> bool:
    """Write `text` to the local OS clipboard. Returns True on success."""
    if _kde_wayland():
        try:
            _klipper().setClipboardContents(text)
            return True
        except Exception as e:
            log.debug("KDE clipboard push failed: %s", e)
            return False
    try:
        pyperclip.copy(text)
        return True
    except pyperclip.PyperclipException as e:
        log.debug("local clipboard push failed: %s", e)
        return False


__all__ = ["available", "push_text", "read_text"]
