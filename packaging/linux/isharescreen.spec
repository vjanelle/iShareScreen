"""Run from any directory with `python -m PyInstaller <this file>`."""
import glob
import os
from pathlib import Path

from PyInstaller.utils.hooks import (
    collect_data_files, collect_dynamic_libs, collect_submodules, copy_metadata,
)

root = Path(SPECPATH).parents[1]
datas = collect_data_files("isharescreen")
datas += copy_metadata("isharescreen", recursive=True)
datas += copy_metadata("PySide6-Essentials", recursive=True)
datas += [(str(root / "LICENSE"), "licenses")]
datas += [(str(path), "licenses") for path in
          (root / "packaging/windows/licenses").glob("*.txt")
          if path.name != "THIRD_PARTY_NOTICES.txt"]
datas += [(str(root / "packaging/linux/THIRD_PARTY_NOTICES.txt"), "licenses")]
binaries = []
hiddenimports = collect_submodules("isharescreen", filter=lambda n: not n.endswith("vtdecode"))
hiddenimports += ["keyring.backends.SecretService", "keyring.backends.kwallet",
                  "dbus.mainloop.glib", "sounddevice", "rendercanvas.glfw",
                  "rendercanvas.offscreen", "wgpu.backends.wgpu_native",
                  "PySide6.QtCore", "PySide6.QtGui", "PySide6.QtWidgets"]
for package in ("av", "wgpu", "glfw", "rendercanvas"):
    datas += collect_data_files(package)
    binaries += collect_dynamic_libs(package)

portaudio = os.environ.get("ISS_PORTAUDIO_LIBRARY")
if not portaudio:
    paths = glob.glob("/usr/lib/*/libportaudio.so.2") + glob.glob("/usr/lib64/libportaudio.so.2")
    portaudio = next(iter(paths), None)
if not portaudio or not Path(portaudio).is_file():
    raise SystemExit("PortAudio missing: install libportaudio2 or set ISS_PORTAUDIO_LIBRARY to its .so.2 file")
binaries.append((str(Path(portaudio).resolve()), "."))
# Preserve the SONAME even when the real library file has a version suffix.
binaries.append((portaudio, "."))

a = Analysis(
    [str(root / "packaging/linux/entry.py")],
    pathex=[str(root / "src")], binaries=binaries, datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "pytest", "PyQt5", "PyQt6", "PySide2",
              "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick"],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="iss", console=True)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="iss")
