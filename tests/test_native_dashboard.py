from __future__ import annotations

import threading

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from isharescreen.gui.native_dashboard import DashboardWindow, _queue_text, _snapshot_document, _uptime
from isharescreen.gui.native_session import NativeSession
from isharescreen.tui.storage import ConnectFormValues


def test_native_dashboard_formats_diagnostics_values():
    assert _uptime(3661) == "1h 1m 1s"
    assert _queue_text({"depth": 3, "cap": 512, "drop": 2}) == "3/512 · 2 drops"
    assert _queue_text(None) == "—"


def test_bug_snapshot_contains_session_metrics_and_log_but_no_password():
    document = _snapshot_document(
        "mac.local",
        {"canvas": {"w": 1920, "h": 1080}, "decoder": "d3d11va"},
        {"loss_total": 4, "rx": {"video_pps": 700}},
        ["connected", "decoded frame"],
    )

    assert document["host"] == "mac.local"
    assert document["session"]["canvas"] == {"w": 1920, "h": 1080}
    assert document["latest"]["loss_total"] == 4
    assert document["log"] == ["connected", "decoded frame"]
    assert "password" not in str(document).lower()


def test_session_choice_dialog_times_out_to_share_current_desktop():
    app = QApplication.instance() or QApplication([])
    window = DashboardWindow(
        NativeSession(),
        ConnectFormValues(
            host="mac.local", user="vincent", password="", advertise="auto",
            audio=True, curtain=True, hdr=False, share_console=False,
            alt_session=False, frontend="desktop",
        ),
    )
    window.SESSION_CHOICE_DIALOG_TIMEOUT_MS = 1
    completed = threading.Event()
    response: dict[str, str] = {}

    window._on_choice_requested("vincent", completed, response)
    assert not completed.is_set()
    assert len(window._choice_dialogs) == 1

    from PySide6.QtTest import QTest
    QTest.qWait(30)

    assert completed.is_set()
    assert response["choice"] == "share_console"
    assert window._choice_dialogs == []
    window.close()
