"""Install an AppImage and desktop launcher for the current user."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import tempfile


def _data_home() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")


def should_offer_install(appimage: str | Path | None) -> bool:
    return bool(appimage) and not (_data_home() / "applications/isharescreen.desktop").exists()


def install_appimage(appimage: str | Path, icon: str | Path) -> None:
    source = Path(appimage).resolve(strict=True)
    binary = Path.home() / ".local/bin/iss"
    binary.parent.mkdir(parents=True, exist_ok=True)
    if source != binary.resolve():
        # Replace atomically, including when an older installed copy is running.
        with tempfile.NamedTemporaryFile(dir=binary.parent, delete=False) as temp:
            temporary = Path(temp.name)
        try:
            shutil.copyfile(source, temporary)
            temporary.chmod(0o755)
            temporary.replace(binary)
        finally:
            temporary.unlink(missing_ok=True)
    data = _data_home()
    icon_target = data / "icons/hicolor/scalable/apps/isharescreen.svg"
    icon_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(icon, icon_target)
    desktop = data / "applications/isharescreen.desktop"
    desktop.parent.mkdir(parents=True, exist_ok=True)
    executable = str(binary).replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%')
    desktop.write_text(
        '[Desktop Entry]\nType=Application\nName=iShareScreen\n'
        'Comment=Connect to a Mac with High Performance Screen Sharing\n'
        f'Exec="{executable}"\nIcon={icon_target}\nTerminal=false\n'
        'Categories=Network;RemoteAccess;\nStartupNotify=true\n', encoding='utf-8'
    )


def offer_install(parent) -> None:
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QMessageBox

    appimage = os.environ.get("APPIMAGE")
    appdir = os.environ.get("APPDIR")
    settings = QSettings()
    if not appdir or not should_offer_install(appimage) or settings.value("appimage/install_offered", False, type=bool):
        return
    answer = QMessageBox.question(
        parent, "Install iShareScreen?",
        "Install iShareScreen for your user and add it to the applications menu?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.Yes,
    )
    settings.setValue("appimage/install_offered", True)
    if answer == QMessageBox.StandardButton.Yes:
        try:
            install_appimage(appimage, Path(appdir) / "isharescreen.svg")
        except OSError as exc:
            settings.remove("appimage/install_offered")
            QMessageBox.warning(parent, "Could not install iShareScreen", str(exc))
