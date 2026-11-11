"""Native PySide6 connection window for Windows."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
    QTextBrowser,
)

from ..tui.storage import ConnectFormValues, load_last

log = logging.getLogger("iss.native.ui")

_RESOLUTIONS = [
    ("Auto — track viewer window", "auto"),
    ("3840 × 2160 · 4K UHD", "3840x2160"),
    ("3440 × 1440 · UWQHD", "3440x1440"),
    ("2560 × 1600 · WQXGA", "2560x1600"),
    ("2560 × 1440 · QHD", "2560x1440"),
    ("1920 × 1200 · WUXGA", "1920x1200"),
    ("1920 × 1080 · Full HD", "1920x1080"),
    ("1680 × 1050 · WSXGA+", "1680x1050"),
    ("1600 × 900 · HD+", "1600x900"),
    ("1366 × 768 · WXGA", "1366x768"),
    ("1280 × 720 · HD", "1280x720"),
    ("1024 × 768 · XGA", "1024x768"),
    ("800 × 600 · SVGA", "800x600"),
]
_SCALES = [("100%", "1.0"), ("150%", "1.5"), ("200%", "2.0"),
           ("250%", "2.5"), ("300%", "3.0"), ("350%", "3.5"), ("400%", "4.0")]
_DECODER_LABELS = {
    "libav-hevc420": "HEVC 4:2:0 · GPU with CPU fallback",
    "vt-hevc444": "HEVC · VideoToolbox",
    "libav-hevc444": "HEVC · Generic GPU decoder",
    "qsv-hevc444": "HEVC · Intel Quick Sync",
    "libav-hevc444-sw": "HEVC · Software decoder",
    "libav-avc420": "H.264",
}


def _form_values(*, host: str, user: str, password: str, resolution: str,
                 scale: str, decoder: str, audio: bool, curtain: bool,
                 hdr: bool, session_mode: str) -> ConnectFormValues:
    mode = session_mode.lower()
    return ConnectFormValues(
        host=host.strip(),
        user=user.strip(),
        password=password,
        advertise=resolution,
        audio=audio,
        curtain=curtain,
        hdr=hdr,
        share_console=mode == "share",
        alt_session=mode == "alternate",
        frontend="desktop",
        dynamic_resolution=resolution == "auto",
        hidpi=scale,
        decoder=decoder or "auto",
        save_password=False,
    )


class ConnectWindow(QMainWindow):
    """Connect form and saved settings; the dashboard owns live sessions."""

    connect_requested = Signal(object)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("iShareScreen")
        self.setMinimumWidth(600)
        self.resize(680, 730)
        self.setObjectName("connectWindow")
        self._last = load_last()
        self._build_ui()
        self._restore_values()
        self._credential_identity: tuple[str, str] | None = None
        self._restore_saved_password()
        self.host.editingFinished.connect(self._restore_saved_password)
        self.user.editingFinished.connect(self._restore_saved_password)
        help_menu = self.menuBar().addMenu("&Help")
        licenses_action = QAction("Open-source licenses", self)
        licenses_action.triggered.connect(self._show_licenses)
        help_menu.addAction(licenses_action)

    def _build_ui(self) -> None:
        central = QWidget(self)
        central.setObjectName("connectSurface")
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(36, 30, 36, 30)
        outer.setSpacing(18)

        brand = QHBoxLayout()
        mark = QLabel("iS")
        mark.setObjectName("brandMark")
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mark.setFixedSize(48, 48)
        heading = QVBoxLayout()
        title = QLabel("iShareScreen")
        title.setObjectName("title")
        subtitle = QLabel("Connect to a Mac screen sharing session")
        subtitle.setObjectName("subtitle")
        heading.addWidget(title)
        heading.addWidget(subtitle)
        brand.addWidget(mark)
        brand.addSpacing(14)
        brand.addLayout(heading, 1)
        outer.addLayout(brand)

        rule = QFrame()
        rule.setFrameShape(QFrame.Shape.HLine)
        rule.setObjectName("rule")
        outer.addWidget(rule)

        self.host = QLineEdit()
        self.host.setPlaceholderText("Mac hostname or IP address")
        self.user = QLineEdit()
        self.user.setPlaceholderText("macOS account name")
        self.password = QLineEdit()
        self.password.setPlaceholderText("Password")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.save_password = QCheckBox("Save password in Windows Credential Manager")
        self.host.setClearButtonEnabled(True)
        self.user.setClearButtonEnabled(True)

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setHorizontalSpacing(24)
        form.setVerticalSpacing(14)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form.addRow("Host", self.host)
        form.addRow("User", self.user)
        form.addRow("Password", self.password)
        form.addRow("", self.save_password)
        section_rule = QFrame()
        section_rule.setFrameShape(QFrame.Shape.HLine)
        section_rule.setObjectName("rule")
        form.addRow(section_rule)

        self.resolution = QComboBox()
        for label, value in _RESOLUTIONS:
            self.resolution.addItem(label, value)
        self.scale = QComboBox()
        for label, value in _SCALES:
            self.scale.addItem(label, value)
        self.decoder = QComboBox()
        self._populate_decoders()
        self.session_mode = QComboBox()
        self.session_mode.addItem("Automatic · ask if someone is signed in", "auto")
        self.session_mode.addItem("Share the current desktop", "share")
        self.session_mode.addItem("Use a separate desktop", "alternate")
        form.addRow("Resolution", self.resolution)
        form.addRow("Display scale", self.scale)
        form.addRow("Video decoder", self.decoder)
        form.addRow("Mac session", self.session_mode)
        outer.addLayout(form)

        checks = QHBoxLayout()
        checks.setSpacing(20)
        self.audio = QCheckBox("Play Mac audio")
        self.curtain = QCheckBox("Blank Mac's physical screen")
        self.hdr = QCheckBox("HDR capable")
        self.curtain.setToolTip("Use a private virtual display while viewing.")
        checks.addWidget(self.audio)
        checks.addWidget(self.curtain)
        checks.addWidget(self.hdr)
        checks.addStretch(1)
        outer.addLayout(checks)

        self.message = QLabel("Your password is used for this session. Saving is controlled by the checkbox.")
        self.message.setObjectName("formMessage")
        self.message.setWordWrap(True)
        outer.addWidget(self.message)

        outer.addStretch(1)
        self.connect_button = QPushButton("Connect")
        self.connect_button.setObjectName("connectButton")
        self.connect_button.setMinimumHeight(46)
        self.connect_button.setDefault(True)
        self.connect_button.clicked.connect(self._on_connect)
        self.password.returnPressed.connect(self._on_connect)
        outer.addWidget(self.connect_button)

    def _populate_decoders(self) -> None:
        self.decoder.addItem("Auto · best available", "auto")
        try:
            from ..proxy.media.registry import all_specs
            for spec in all_specs():
                try:
                    if not spec.supported_here():
                        continue
                except Exception:
                    continue
                label = _DECODER_LABELS.get(spec.name, spec.name)
                self.decoder.addItem(label, spec.name)
        except Exception as exc:
            log.warning("decoder choices unavailable: %s", exc)

    def _restore_values(self) -> None:
        last = self._last
        if last is None:
            self.resolution.setCurrentIndex(0)
            self.scale.setCurrentIndex(0)
            self.audio.setChecked(True)
            self.curtain.setChecked(True)
            return
        self.host.setText(last.host)
        self.user.setText(last.user)
        self._select_data(self.resolution, last.advertise or "auto")
        self._select_data(self.scale, last.hidpi if last.hidpi != "auto" else "1.0")
        self._select_data(self.decoder, last.decoder)
        self._select_data(self.session_mode,
                          "alternate" if last.alt_session else "share" if last.share_console else "auto")
        self.audio.setChecked(last.audio)
        self.curtain.setChecked(last.curtain)
        self.hdr.setChecked(last.hdr)

    def _restore_saved_password(self) -> None:
        identity = (self.host.text().strip(), self.user.text().strip())
        if identity == self._credential_identity:
            return
        self._credential_identity = identity
        self.password.clear()
        self.save_password.setChecked(False)
        if not all(identity):
            return
        try:
            from .windows_credentials import read_password
            password = read_password(*identity)
        except OSError as exc:
            log.warning("could not read saved credential: %s", exc)
            return
        if password is not None:
            self.password.setText(password)
            self.save_password.setChecked(True)

    @staticmethod
    def _select_data(combo: QComboBox, value: str) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _on_connect(self) -> None:
        host = self.host.text().strip()
        user = self.user.text().strip()
        password = self.password.text()
        if not host or not user or not password:
            self.show_error("Enter the Mac host, account name, and password to connect.")
            return
        values = _form_values(
            host=host,
            user=user,
            password=password,
            resolution=str(self.resolution.currentData()),
            scale=str(self.scale.currentData()),
            decoder=str(self.decoder.currentData()),
            audio=self.audio.isChecked(),
            curtain=self.curtain.isChecked(),
            hdr=self.hdr.isChecked(),
            session_mode=str(self.session_mode.currentData()),
        )
        values.save_password = self.save_password.isChecked()
        self.connect_button.setEnabled(False)
        self.connect_button.setText("Starting…")
        self.message.setText("Starting the native viewer…")
        self.message.setObjectName("formMessage")
        self.style().unpolish(self.message)
        self.style().polish(self.message)
        self.connect_requested.emit(values)

    def show_error(self, message: str) -> None:
        self.message.setText(message)
        self.message.setObjectName("formError")
        self.connect_button.setEnabled(True)
        self.connect_button.setText("Connect")
        self.style().unpolish(self.message)
        self.style().polish(self.message)

    def reset_after_disconnect(self) -> None:
        self.password.clear()
        self._credential_identity = None
        self._restore_saved_password()
        self.connect_button.setEnabled(True)
        self.connect_button.setText("Connect")
        self.message.setText("Your password is used for this session. Saving is controlled by the checkbox.")

    def _show_licenses(self) -> None:
        root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[3]))
        license_dir = root / "licenses"
        if not license_dir.exists():
            license_dir = Path(__file__).resolve().parents[3] / "packaging" / "windows" / "licenses"
        license_files = sorted(license_dir.glob("*.txt"))
        project_license = license_dir / "AGPL-3.0.txt"
        if not project_license.exists():
            project_license = license_dir / "LICENSE"
        if not project_license.exists():
            project_license = root / "LICENSE"
        if not project_license.exists():
            project_license = Path(__file__).resolve().parents[3] / "LICENSE"
        license_files.append(project_license)
        sections = []
        for path in license_files:
            try:
                sections.append(f"===== {path.name} =====\n\n{path.read_text(encoding='utf-8')}")
            except OSError:
                continue
        dialog = QDialog(self)
        dialog.setWindowTitle("Open-source licenses")
        dialog.resize(720, 620)
        layout = QVBoxLayout(dialog)
        browser = QTextBrowser(dialog)
        browser.setOpenExternalLinks(True)
        browser.setPlainText("\n\n".join(sections) or "License information is unavailable.")
        layout.addWidget(browser)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(dialog.reject)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)
        dialog.exec()


__all__ = ["ConnectWindow", "_form_values"]
