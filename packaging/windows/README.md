# Windows one-file build

Build on Windows x64 with Python 3.12 or newer. The build machine needs an
internet connection for the first dependency installation; the resulting app
does not need Python installed on the viewing machine.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[windows-build]"
python -m PyInstaller --noconfirm --clean packaging/windows/isharescreen.spec
```

The distributable is `dist\iShareScreen.exe`. It is a single windowed
executable containing Python, PySide6 Essentials, the iShareScreen runtime,
Qt plugins, decoder resources, and required native dependencies. Windows will
still need a working GPU driver for the native viewer; audio playback also
needs an available output device.

The executable starts the native connect window. Use Help → Open-source
licenses to view the included iShareScreen license, complete Qt licensing
texts, and third-party notices offline.

Builds are architecture-specific. To produce an ARM64 executable, use an
ARM64 Python environment and confirm that all native dependency wheels are
available for that architecture.

## MSI installer

Install the .NET 6 SDK or newer, then run the MSI packager from PowerShell:

```powershell
.\packaging\windows\build-msi.ps1
```

The script rebuilds the EXE and writes `dist\iShareScreen.msi`. To package an
already-built EXE without rerunning PyInstaller, use
`.\packaging\windows\build-msi.ps1 -SkipExeBuild`. The MSI uses a standard
install wizard, installs per-user under `%LOCALAPPDATA%\Programs\iShareScreen`
by default, adds a Start Menu shortcut, and supports upgrades and removal
through Windows Settings. It does not require administrator rights.
