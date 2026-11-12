"""PySide6 application entry point for the Windows desktop UI."""
from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:  # useful when using the optional Windows extra
        print(
            "The native Windows interface requires PySide6. Install it with "
            "`pip install 'isharescreen[windows]'`.",
            file=sys.stderr,
        )
        return 1

    from .native_connect import ConnectWindow
    from .native_session import NativeSession

    app = QApplication(argv or sys.argv)
    app.setApplicationName("iShareScreen")
    app.setOrganizationName("iShareScreen")
    app.setQuitOnLastWindowClosed(True)
    app.setStyle("Fusion")
    app.setStyleSheet(_APP_STYLE)
    controller = _NativeController(ConnectWindow(), NativeSession())
    controller.connect_window.show()
    return app.exec()


class _NativeController:
    """Own the connect window, dashboard, and one session worker."""

    def __init__(self, connect_window, session):
        self.connect_window = connect_window
        self.session = session
        self.dashboard = None
        self.connect_window.connect_requested.connect(self._connect)

    def _connect(self, values) -> None:
        from .native_dashboard import DashboardWindow
        self.connect_window.hide()
        self.dashboard = DashboardWindow(self.session, values)
        self.dashboard.close_requested.connect(self._return_to_connect)
        self.dashboard.show()
        self.session.start(values)

    def _return_to_connect(self) -> None:
        self.connect_window.reset_after_disconnect()
        self.connect_window.show()
        self.connect_window.raise_()
        self.connect_window.activateWindow()
        self.dashboard = None


_APP_STYLE = """
QWidget { background: #15181e; color: #e9edf3; font-family: 'Segoe UI'; font-size: 10pt; }
QMainWindow { background: #15181e; }
QLabel#title { font-size: 21pt; font-weight: 650; color: #f7f9fc; }
QLabel#subtitle { color: #9aa6b7; font-size: 10pt; }
QLabel#brandMark { background: #2768e8; color: white; border-radius: 12px; font-size: 17pt; font-weight: 700; }
QFrame#rule { color: #2a303b; }
QLineEdit, QComboBox, QPlainTextEdit {
  background: #20252e; color: #edf1f7; border: 1px solid #343c49;
  border-radius: 7px; padding: 8px 10px; selection-background-color: #2768e8;
}
QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus { border-color: #4e8cff; }
QComboBox::drop-down { border: 0; width: 26px; }
QComboBox QAbstractItemView { background: #20252e; color: #edf1f7; selection-background-color: #2768e8; }
QPushButton {
  background: #252b35; color: #edf1f7; border: 1px solid #3b4553;
  border-radius: 7px; padding: 9px 15px; font-weight: 600;
}
QPushButton:hover { background: #303948; border-color: #56657a; }
QPushButton:disabled { color: #778292; background: #20242a; }
QPushButton#connectButton { background: #2768e8; border-color: #2768e8; color: white; }
QPushButton#connectButton:hover { background: #3978f3; }
QCheckBox { spacing: 8px; color: #cad2df; }
QCheckBox::indicator { width: 17px; height: 17px; }
QCheckBox::indicator:unchecked { background: #20252e; border: 1px solid #485363; border-radius: 4px; }
QCheckBox::indicator:checked { background: #2768e8; border: 1px solid #5590ff; border-radius: 4px; }
QLabel#formMessage { color: #9aa6b7; }
QLabel#formError { color: #ff8585; }
QLabel#sessionHeader { color: #aab6c6; background: #1c222b; border: 1px solid #2a3340; border-radius: 8px; padding: 10px 12px; }
QLabel#statusPill { background: #202b3b; color: #a9c6ff; border-radius: 10px; padding: 6px 12px; font-weight: 650; }
QLabel#metricName { color: #9aa6b7; padding: 3px 0; }
QLabel#metricValue { color: #edf1f7; font-weight: 600; padding: 3px 0; }
QLabel#tileSummary { color: #bac5d3; }
QGroupBox { border: 1px solid #2d3541; border-radius: 9px; margin-top: 12px; padding: 14px 12px 10px; font-weight: 650; color: #d9e1eb; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 5px; }
QScrollBar:vertical { background: #1a1f27; width: 12px; margin: 0; }
QScrollBar::handle:vertical { background: #3c4655; min-height: 24px; border-radius: 5px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""
