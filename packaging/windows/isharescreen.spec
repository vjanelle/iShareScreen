# PyInstaller one-file Windows build for iShareScreen.
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, copy_metadata

ROOT = Path(SPECPATH).resolve().parents[1]
ENTRY = ROOT / "src" / "isharescreen" / "tui" / "entry.py"

datas = collect_data_files(
    "isharescreen",
    includes=["proxy/media/samples/*.hevc", "proxy/media/samples/README.md"],
)
datas += [(str(ROOT / "LICENSE"), "licenses")]
datas += [
    (str(path), "licenses")
    for path in (ROOT / "packaging" / "windows" / "licenses").glob("*.txt")
]

binaries = collect_dynamic_libs("glfw")
hiddenimports = [
    "isharescreen.gui.native_entry",
    "isharescreen.gui.native_connect",
    "isharescreen.gui.native_dashboard",
    "isharescreen.gui.native_session",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "rendercanvas.glfw",
]

# PyInstaller's standard hooks for PyAV, wgpu, rendercanvas, sounddevice,
# cryptography, NumPy, and Qt collect their required runtime DLLs/resources.
# Collecting entire package trees would pull test suites and unused backends.

# Retain dependency metadata/license files inside the one-file archive.
for distribution in (
    "PySide6_Essentials", "shiboken6", "av", "cryptography", "pycryptodome",
    "numpy", "aioquic", "aiohttp", "wgpu", "rendercanvas", "glfw",
    "sounddevice", "pyperclip",
):
    datas += copy_metadata(distribution, recursive=True)

a = Analysis(
    [str(ENTRY)],
    pathex=[str(ROOT / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="iShareScreen",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
