# iShareScreen

Cross-platform Python client for Apple's macOS Screen Sharing **High
Performance** mode (HEVC RExt 4:4:4 over UDP/SRTP). Renders the host
Mac's screen in a native wgpu window with hardware decode where
available.

## Setup

### On the host Mac (the target you want to view)

1. Any modern macOS that supports the Screen Sharing app's High
   Performance mode (Apple Silicon, recent macOS).
2. *System Settings → General → Sharing → **Screen Sharing*** → toggle on.

### On the viewing machine

#### macOS

1. Install Python 3.10 or later (from [python.org](https://www.python.org/downloads/),
   `brew install python`, or `uv python install 3.13`).
2. Install iShareScreen:
   ```sh
   pip install git+https://github.com/renegadelink/iShareScreen.git
   ```

#### Windows

1. Install Python 3.10 or later from [python.org](https://www.python.org/downloads/)
   (the installer includes pip; check "Add python.exe to PATH" during install).
2. Open PowerShell or cmd and run:
   ```sh
   pip install git+https://github.com/renegadelink/iShareScreen.git
   ```

3. (Optional, only if you want audio) install **libfdk-aac** — Apple's
   PT=101 audio uses AAC-ELD-SBR, which Windows Media Foundation can't
   decode. The cleanest source is [MSYS2](https://www.msys2.org):
   ```sh
   pacman -Sy --noconfirm mingw-w64-x86_64-fdk-aac
   ```
   This drops `libfdk-aac-2.dll` at `C:\msys64\mingw64\bin\`, which iss
   searches automatically. If you already have [scoop](https://scoop.sh),
   `scoop install msys2` followed by the same `pacman` command also
   works — iss looks under `%USERPROFILE%\scoop\apps\msys2\current\mingw64\bin`
   too. Without libfdk-aac, video works as normal and audio is silently
   skipped.

#### Linux (Debian / Ubuntu)

For a standalone viewer, use the **x86_64 AppImage** from the Linux AppImage
CI artifact (unzip the artifact first):

```sh
chmod +x iShareScreen-0.1.0-x86_64.AppImage
./iShareScreen-0.1.0-x86_64.AppImage
```

Python, application dependencies, and PortAudio are bundled. CI builds on
Ubuntu 22.04 (glibc 2.35 baseline); locally built images require the build
host's glibc or newer. Your desktop supplies its browser, graphics drivers,
and D-Bus session. The connection form opens in your browser; select
**desktop (native window)** for the native video viewer. The browser video
frontend requires a browser supporting WebTransport and WebCodecs.

If FUSE is unavailable, extract and run instead:

```sh
./iShareScreen-0.1.0-x86_64.AppImage --appimage-extract
./squashfs-root/AppRun
```

On Linux, **Remember password in desktop keyring** saves the submitted
host/account password using GNOME Keyring (Secret Service) or KDE Wallet
(Plasma 5/6). Leave the password field blank to use the saved credential.
**Forget saved password** deletes the entry for the host/account currently
entered. Connecting with Remember unchecked also removes that saved entry.
Your desktop may ask to unlock or grant access to its keyring. If access
fails, enter the password manually; there is no plaintext storage fallback.
Passwords are never embedded in the connection page or its JSON settings.
CLI `--password-stdin` continues to work without accessing the keyring.

Optional host packages: `libfdk-aac2` for AAC-ELD-SBR audio decoding,
`xclip` (X11) or `wl-clipboard` (Wayland) for clipboard synchronization,
and your GPU's VAAPI driver for hardware video decoding. These packages
are separate from the Python environment bundled in the image.

HEVC hardware selection also tries Vulkan through PyAV's `HWAccel` API.
The linked FFmpeg must include that decoder backend, and the GPU/driver
must support the stream's HEVC RExt 4:4:4 profile. Vulkan rendering support
alone does not establish Vulkan video decoding support. Standard PyAV Linux
wheels may omit VAAPI and Vulkan: installing Mesa drivers does not add those
backends to an already bundled FFmpeg. The viewer probes a real sample and
uses AVC when hardware HEVC 4:4:4 is unavailable.

To install from source instead:

1. Install Python and the system libraries that the GPU + window stack
   need (Vulkan loader, OpenGL, X11 / Wayland surfaces, PortAudio,
   AAC-ELD-SBR audio decoder):
   ```sh
   sudo apt install python3 python3-pip python3-venv \
       libvulkan1 libgl1 libegl1 \
       libxrandr2 libxinerama1 libxcursor1 libxi6 \
       libportaudio2 libfdk-aac2 \
       build-essential pkg-config python3-dev libdbus-1-dev libglib2.0-dev \
       xclip
   ```
   `libfdk-aac2` is only used for audio; if you skip it, video still
   works and audio is silently disabled.

   `xclip` enables bidirectional clipboard sync with the macOS host. On
   Wayland desktops use `wl-clipboard` instead. If neither is installed
   iss logs a one-line warning at startup and runs without clipboard
   sync — everything else still works.
2. (Optional, for hardware HEVC decode on Intel GPUs) install vaapi:
   ```sh
   sudo apt install vainfo intel-media-va-driver-non-free
   ```
   For AMD, swap the driver: `sudo apt install mesa-va-drivers`.
3. Install iShareScreen (in a venv recommended):
   ```sh
   python3 -m venv ~/.venvs/iss
   ~/.venvs/iss/bin/pip install git+https://github.com/renegadelink/iShareScreen.git
   ~/.venvs/iss/bin/iss     # or symlink to ~/.local/bin
   ```

For Fedora / Arch / openSUSE, translate the apt package names with your
distro's package manager (most are named the same or very close).

### Building the Linux AppImage

Build on Ubuntu 22.04 x86_64 for the supported baseline. Newer build hosts
produce images requiring their newer glibc. No macOS host is needed to build.

```sh
sudo apt install python3 python3-venv build-essential pkg-config \
    libdbus-1-dev libglib2.0-dev libportaudio2 curl
python3 -m venv .venv-build
.venv-build/bin/python -m pip install '.[test]' -r packaging/linux/requirements-build.txt
.venv-build/bin/python -m pytest
PYTHON=.venv-build/bin/python packaging/linux/build.sh
```

The build downloads checksum-verified appimagetool 1.9.1 and produces
`dist/iShareScreen-0.1.0-x86_64.AppImage` plus its SHA-256 checksum.
It reuses that tool's embedded runtime, so no floating runtime download is
needed. `APPIMAGETOOL=/path/to/appimagetool.AppImage` can supply a trusted
local tool instead; you are responsible for verifying an override.
`ISS_PORTAUDIO_LIBRARY=/path/to/libportaudio.so.2` can supply a library
outside standard distro paths. Exact installed package versions and the
build's glibc are recorded in `usr/share/doc/isharescreen/build-info.json`
inside the image. Python dependency ranges remain as declared in
`pyproject.toml`; the build is repeatable but is not bit-for-bit reproducible.

The `Linux AppImage` GitHub Actions workflow runs tests and builds an artifact;
it does not publish a release.

### Firewall

iss connects to the host Mac over **TCP 5900** (control) plus two UDP
flows: **5900** (audio + RTCP) and **5901** (video). It sends from both
UDP ports during connect. If a firewall still blocks the stream, allow
UDP 5900–5901 inbound.

## Usage

```sh
iss
```

Opens a browser connection form for host / username / password (masked)
and resolution, then a live diagnostics dashboard. Video streams in a
browser tab or native window. The last host, username, frontend, and
remember-password preference pre-fill the form on the next launch.
Passwords are stored only when requested, in the Linux desktop keyring.

Any flag accepted by `iss --headless` also pre-fills the form, so
launchers can do:

```sh
iss --host mac.local -u me --advertise 1920x1080 --no-curtain
```

Useful keys in the live session: **f** force IDR refresh (fixes the
rare gray patch the auto-recovery doesn't catch), **r** reconnect,
**d** disconnect, **Ctrl-B** save a bug-report snapshot, **q** quit.

For CI / scripted use:

```sh
echo "$PASSWORD" | iss --headless --host mac.local -u me --password-stdin --auto-quit-secs 30
```

## License

AGPL-3.0-or-later. See [LICENSE](LICENSE).

This is an independent reverse-engineering of a publicly-documented
network protocol. No Apple source code, headers, or symbols are
included.
