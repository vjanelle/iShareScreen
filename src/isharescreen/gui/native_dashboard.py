"""Native session status, diagnostics, controls, and prompts."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..tui.storage import ConnectFormValues, bug_snapshot_path
from .native_session import NativeSession


class DashboardWindow(QMainWindow):
    """Live, native view of a running session."""

    SESSION_CHOICE_DIALOG_TIMEOUT_MS = 45_000

    close_requested = Signal()

    def __init__(self, session: NativeSession, values: ConnectFormValues,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.session = session
        self.values = values
        self._closing = False
        self._hello_data: dict[str, Any] = {}
        self._latest_snapshot: dict[str, Any] = {}
        self._log_lines: list[str] = []
        self._choice_dialogs: list[QMessageBox] = []
        self.setWindowTitle("iShareScreen · Session")
        self.resize(1020, 760)
        self.setMinimumSize(760, 600)
        self._metrics: dict[str, QLabel] = {}
        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(24, 22, 24, 22)
        outer.setSpacing(14)

        top = QHBoxLayout()
        title_col = QVBoxLayout()
        title = QLabel("Session diagnostics")
        title.setObjectName("title")
        self.host_label = QLabel(self.values.host)
        self.host_label.setObjectName("subtitle")
        title_col.addWidget(title)
        title_col.addWidget(self.host_label)
        top.addLayout(title_col, 1)
        self.status_label = QLabel("Connecting…")
        self.status_label.setObjectName("statusPill")
        top.addWidget(self.status_label, 0, Qt.AlignmentFlag.AlignVCenter)
        outer.addLayout(top)

        self.header_label = QLabel("Waiting for the Mac to respond…")
        self.header_label.setObjectName("sessionHeader")
        self.header_label.setWordWrap(True)
        outer.addWidget(self.header_label)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        self._add_card(grid, 0, 0, "Stream", ["canvas", "tiles", "decoder", "uptime"])
        self._add_card(grid, 0, 1, "Network", ["video_rx", "audio_rx", "rtcp_rx", "uplink"])
        self._add_card(grid, 1, 0, "Loss and health", ["loss", "unmapped", "last_publish", "ssrc"])
        self._add_card(grid, 1, 1, "Queues and decode", ["video_queue", "control_queue", "decode_queue", "decode_latency"])
        outer.addLayout(grid)

        self.tile_label = QLabel("Per-tile activity will appear when frames arrive.")
        self.tile_label.setObjectName("tileSummary")
        self.tile_label.setWordWrap(True)
        outer.addWidget(self.tile_label)

        log_box = QGroupBox("Session log")
        log_layout = QVBoxLayout(log_box)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(4000)
        self.log_view.setPlaceholderText("Connection and decoder messages appear here.")
        log_layout.addWidget(self.log_view)
        outer.addWidget(log_box, 1)

        actions = QHBoxLayout()
        actions.addStretch(1)
        self.force_button = QPushButton("Force IDR")
        self.reconnect_button = QPushButton("Reconnect")
        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.setObjectName("connectButton")
        self.snapshot_button = QPushButton("Save bug snapshot")
        actions.addWidget(self.force_button)
        actions.addWidget(self.snapshot_button)
        actions.addWidget(self.reconnect_button)
        actions.addWidget(self.disconnect_button)
        outer.addLayout(actions)

        self.force_button.clicked.connect(lambda: self.session.send_action({"action": "fir"}))
        self.reconnect_button.clicked.connect(self._reconnect)
        self.disconnect_button.clicked.connect(self._disconnect)
        self.snapshot_button.clicked.connect(self._save_snapshot)

    def _add_card(self, grid: QGridLayout, row: int, col: int,
                  title: str, keys: list[str]) -> None:
        box = QGroupBox(title)
        layout = QGridLayout(box)
        for index, key in enumerate(keys):
            label = QLabel(self._label_for(key))
            label.setObjectName("metricName")
            value = QLabel("—")
            value.setObjectName("metricValue")
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            layout.addWidget(label, index, 0)
            layout.addWidget(value, index, 1, Qt.AlignmentFlag.AlignRight)
            self._metrics[key] = value
        grid.addWidget(box, row, col)

    @staticmethod
    def _label_for(key: str) -> str:
        return {
            "canvas": "Canvas",
            "tiles": "Decoded tiles",
            "decoder": "Decoder",
            "uptime": "Uptime",
            "video_rx": "Video receive",
            "audio_rx": "Audio receive",
            "rtcp_rx": "RTCP receive",
            "uplink": "Control uplink",
            "loss": "Lost packets",
            "unmapped": "Unmapped loss",
            "last_publish": "Last frame",
            "ssrc": "Stream groups",
            "video_queue": "UDP video queue",
            "control_queue": "UDP control queue",
            "decode_queue": "Decode queue",
            "decode_latency": "Decode latency",
        }[key]

    def _connect_signals(self) -> None:
        self.session.status.connect(self._on_status)
        self.session.hello.connect(self._on_hello)
        self.session.snapshot.connect(self._on_snapshot)
        self.session.event.connect(self._on_event)
        self.session.log_line.connect(self._append_log)
        self.session.finished.connect(self._on_finished)
        self.session.choice_requested.connect(self._on_choice_requested)

    def _on_status(self, data: dict[str, Any]) -> None:
        status = data.get("status", "unknown")
        self.status_label.setText(status.capitalize())
        if data.get("host"):
            self.host_label.setText(str(data["host"]))
        if status == "error":
            self.header_label.setText(str(data.get("message") or "Could not start the session."))
        elif status == "connecting":
            self.header_label.setText("Connecting to the Mac and opening the native viewer…")
        elif status == "running":
            self.header_label.setText("Connected · video is shown in the native viewer window.")
        elif status in ("ended", "disconnected"):
            self.header_label.setText("Session ended. Reconnect, or return to the connect form.")
            self.disconnect_button.setText("Back to Connect")

    def _on_hello(self, data: dict[str, Any]) -> None:
        self._hello_data = dict(data)
        canvas = data.get("canvas") or {}
        size = " × ".join(str(canvas.get(k, "?")) for k in ("w", "h"))
        count = canvas.get("tiles")
        self._metrics["canvas"].setText(size)
        self._metrics["tiles"].setText(str(count if count is not None else "—"))
        self._metrics["decoder"].setText(str(data.get("decoder") or "—"))
        if data.get("host"):
            self.host_label.setText(str(data["host"]))
        self.header_label.setText(
            f"{data.get('host', self.values.host)} · {size} · {count or 0} tiles · "
            f"{data.get('decoder', 'decoder pending')}"
        )

    def _on_snapshot(self, data: dict[str, Any]) -> None:
        self._latest_snapshot = dict(data)
        rx = data.get("rx") or {}
        udp = data.get("udp_q") or {}
        tiles = data.get("tiles") or []
        self._set("decoder", data.get("decoder"))
        self._set("uptime", _uptime(data.get("uptime_s")))
        self._set("video_rx", f"{rx.get('video_pps', 0)} pps · {rx.get('video_mbps', 0)} Mbps")
        self._set("audio_rx", f"{rx.get('audio_pps', 0)} pps · {rx.get('audio_kbps', 0)} kbps")
        self._set("rtcp_rx", f"{rx.get('rtcp_pps', 0)} pps · {rx.get('rtcp_kbps', 0)} kbps")
        self._set("uplink", f"{(data.get('tx') or {}).get('pps', 0)} pps")
        self._set("loss", data.get("loss_total"))
        self._set("unmapped", data.get("loss_unmapped"))
        age = data.get("last_publish_age_s")
        self._set("last_publish", f"{age}s ago" if age is not None else None)
        self._set("ssrc", data.get("ssrc_groups"))
        self._set("video_queue", _queue_text(udp.get("video")))
        self._set("control_queue", _queue_text(udp.get("ctrl")))
        self._set("decode_queue", _queue_text(data.get("decode_q")))
        latency = data.get("decode_latency_ms")
        self._set("decode_latency", f"{latency} ms" if latency is not None else None)
        if tiles:
            summary = "   ·   ".join(
                f"Tile {index}: {tile.get('fps', 0):.1f} fps"
                + (f", {tile.get('loss_s', 0)} lost" if tile.get("loss_s") else "")
                for index, tile in enumerate(tiles)
            )
            self.tile_label.setText(summary)
        elif self._hello_data.get("canvas"):
            self.tile_label.setText("Waiting for decoded tile frames…")

    def _on_event(self, data: dict[str, Any]) -> None:
        kind = data.get("kind", "event")
        if kind == "error":
            self.status_label.setText("Connection error")
        self._append_log(f"[{kind}] {data}")

    def _append_log(self, line: str) -> None:
        self._log_lines.append(line)
        del self._log_lines[:-4000]
        self.log_view.appendPlainText(line)
        cursor = self.log_view.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.log_view.setTextCursor(cursor)

    def _set(self, key: str, value: Any) -> None:
        self._metrics[key].setText("—" if value is None or value == "" else str(value))

    def _on_choice_requested(self, console_user: str,
                             response_event: Any, response: dict[str, str]) -> None:
        user_text = f"{console_user} is signed in at the Mac." if console_user else "Someone is signed in at the Mac."
        box = QMessageBox(self)
        box.setWindowTitle("Choose Mac session")
        box.setIcon(QMessageBox.Icon.Question)
        box.setText(user_text)
        box.setInformativeText("Share the current desktop, or sign in on a separate display?")
        share = box.addButton("Share current desktop", QMessageBox.ButtonRole.AcceptRole)
        alternate = box.addButton("Use separate desktop", QMessageBox.ButtonRole.ActionRole)
        box.setDefaultButton(share)
        self._choice_dialogs.append(box)
        completed = False

        def finish(_result: int = 0) -> None:
            nonlocal completed
            if completed:
                return
            completed = True
            selected = "alt_session" if box.clickedButton() is alternate else "share_console"
            self.session.answer_session_choice(response_event, response, selected)
            if box in self._choice_dialogs:
                self._choice_dialogs.remove(box)

        box.finished.connect(finish)
        QTimer.singleShot(self.SESSION_CHOICE_DIALOG_TIMEOUT_MS, box.reject)
        box.open()

    def _reconnect(self) -> None:
        self.log_view.appendPlainText("[ui] reconnecting")
        self.session.start(self.values)

    def _disconnect(self) -> None:
        self.session.stop()
        self.status_label.setText("Disconnected")
        self.header_label.setText("Session disconnected.")
        self.disconnect_button.setText("Back to Connect")
        self.close_requested.emit()
        self._closing = True
        self.close()

    def _save_snapshot(self) -> None:
        try:
            path = bug_snapshot_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            document = _snapshot_document(
                self.values.host, self._hello_data, self._latest_snapshot, self._log_lines,
            )
            path.write_text(json.dumps(document, indent=2), encoding="utf-8")
            QMessageBox.information(self, "Bug snapshot saved", f"Saved to:\n{path}")
        except OSError as exc:
            QMessageBox.warning(self, "Could not save snapshot", str(exc))

    def _on_finished(self, code: int) -> None:
        if code != 0:
            self._append_log(f"[ui] session worker exited with code {code}")
        self.status_label.setText("Ended" if code == 0 else "Session error")
        self.header_label.setText("Session ended. Reconnect, or return to the connect form.")
        self.disconnect_button.setText("Back to Connect")

    def closeEvent(self, event) -> None:  # noqa: N802
        self.session.stop()
        if not self._closing:
            self._closing = True
            self.close_requested.emit()
        event.accept()


def _uptime(value: Any) -> str:
    seconds = max(0, int(value or 0))
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m {seconds}s"
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def _queue_text(value: Any) -> str:
    if not isinstance(value, dict):
        return "—"
    return f"{value.get('depth', 0)}/{value.get('cap', 0)} · {value.get('drop', 0)} drops"


def _snapshot_document(host: str, hello: dict[str, Any],
                       snapshot: dict[str, Any], log_lines: list[str]) -> dict[str, Any]:
    return {
        "format": "isharescreen-bug-snapshot-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "host": host,
        "session": dict(hello),
        "latest": dict(snapshot),
        "log": list(log_lines[-4000:]),
    }


__all__ = ["DashboardWindow"]
