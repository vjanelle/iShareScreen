"""Source/frozen launch compatibility."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def session_command() -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable]
    return [sys.executable, "-m", "isharescreen.cli"]


def configure_environment() -> None:
    """Keep external browsers/clipboard tools on the host's library path.

    The Linux loader has already initialized its own search path when the
    bootloader starts Python. Restore the environment inherited by future
    children. Frozen children initialize their own bootloader normally.
    """
    if getattr(sys, "frozen", False) and sys.platform.startswith("linux"):
        original = os.environ.get("LD_LIBRARY_PATH_ORIG")
        if original:
            os.environ["LD_LIBRARY_PATH"] = original
        else:
            os.environ.pop("LD_LIBRARY_PATH", None)
        # Qt is relocated by the embedded qt.conf installed by PyInstaller.
        # Remove private plugin paths from the environment inherited by host
        # tools, which may use an incompatible system Qt (e.g. KDE helpers).
        bundle_root = Path(getattr(sys, "_MEIPASS", "/__iss_not_frozen__"))
        for key in ("QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH", "QML2_IMPORT_PATH"):
            if key not in os.environ:
                continue
            paths = [p for p in os.environ[key].split(os.pathsep)
                     if p and not Path(p).is_relative_to(bundle_root)]
            if paths:
                os.environ[key] = os.pathsep.join(paths)
            else:
                os.environ.pop(key, None)
        # sounddevice asks ctypes.util.find_library before loading PortAudio.
        # Linux's ldconfig cache knows nothing about our private bundle.
        import ctypes.util
        bundled = Path(getattr(sys, "_MEIPASS", "")) / "libportaudio.so.2"
        if bundled.is_file():
            original_find = ctypes.util.find_library

            def find_library(name):
                return str(bundled) if name == "portaudio" else original_find(name)

            ctypes.util.find_library = find_library
