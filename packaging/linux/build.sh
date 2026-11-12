#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$root"
python=${PYTHON:-python3}
arch=$(uname -m)
if [[ $(uname -s) != Linux || $arch != x86_64 ]]; then
    echo 'This build currently targets Linux x86_64 only.' >&2
    exit 1
fi
"$python" -c 'import PyInstaller, isharescreen, dbus, secretstorage, keyring'
version=$("$python" -c 'from isharescreen import __version__; print(__version__)')
mkdir -p build/appimage-tools dist
tool=${APPIMAGETOOL:-"$root/build/appimage-tools/appimagetool-1.9.1-x86_64.AppImage"}
if [[ ! -f $tool ]]; then
    curl -fL --retry 3 'https://github.com/AppImage/appimagetool/releases/download/1.9.1/appimagetool-x86_64.AppImage' -o "$tool"
fi
if [[ -z ${APPIMAGETOOL:-} ]]; then
    echo "ed4ce84f0d9caff66f50bcca6ff6f35aae54ce8135408b3fa33abfc3cb384eb0  $tool" | sha256sum -c -
fi
tool=$(realpath "$tool")
chmod +x "$tool"
# Reuse this tool's pinned type-2 runtime; avoid a second, floating download.
offset=$("$tool" --appimage-offset)
[[ $offset =~ ^[0-9]+$ ]]
runtime="$root/build/appimage-tools/runtime-$arch"
head -c "$offset" "$tool" > "$runtime"

"$python" -m PyInstaller --noconfirm --clean \
    --distpath build/appimage-payload --workpath build/pyinstaller \
    packaging/linux/isharescreen.spec

appdir="$root/build/iShareScreen.AppDir"
mkdir -p "$appdir/usr/bin" "$appdir/usr/share/doc/isharescreen"
# Replace only the generated payload so deleted modules cannot linger.
"$python" - "$root/build/appimage-payload/iss" "$appdir/usr/bin" <<'PY'
import pathlib, shutil, sys
source, target = map(pathlib.Path, sys.argv[1:])
for child in target.iterdir():
    if child.is_dir() and not child.is_symlink():
        shutil.rmtree(child)
    else:
        child.unlink()
shutil.copytree(source, target, dirs_exist_ok=True, symlinks=True)
PY
install -m755 packaging/linux/AppRun "$appdir/AppRun"
install -m644 packaging/linux/isharescreen.desktop "$appdir/isharescreen.desktop"
install -m644 packaging/linux/isharescreen.svg "$appdir/isharescreen.svg"
cp packaging/linux/isharescreen.svg "$appdir/.DirIcon"
cp LICENSE README.md "$appdir/usr/share/doc/isharescreen/"
portaudio_license=${ISS_PORTAUDIO_LICENSE:-/usr/share/doc/libportaudio2/copyright}
if [[ -f $portaudio_license ]]; then
    cp "$portaudio_license" "$appdir/usr/share/doc/isharescreen/PortAudio-copyright"
fi
"$python" - "$appdir/usr/share/doc/isharescreen/build-info.json" <<'PY'
import importlib.metadata as m
import json, platform, sys
from pathlib import Path
Path(sys.argv[1]).write_text(json.dumps({
    "python": platform.python_version(), "libc": platform.libc_ver(),
    "packages": {d.metadata["Name"]: d.version for d in m.distributions()},
}, indent=2) + "\n")
PY
image="$root/dist/iShareScreen-$version-$arch.AppImage"
staging=$(mktemp -d "$root/dist/.appimage-build.XXXXXX")
ARCH="$arch" "$tool" --appimage-extract-and-run --no-appstream \
    --mksquashfs-opt=-processors --mksquashfs-opt=2 \
    --runtime-file "$runtime" "$appdir" "$staging/iShareScreen.AppImage"
# Replace only a completed image. Linux allows this rename even while the
# previous executable is running; opening that executable for writing fails.
mv -f -- "$staging/iShareScreen.AppImage" "$image"
rmdir -- "$staging"
sha256sum "dist/iShareScreen-$version-$arch.AppImage" > "dist/iShareScreen-$version-$arch.AppImage.sha256"
echo "Built dist/iShareScreen-$version-$arch.AppImage"
