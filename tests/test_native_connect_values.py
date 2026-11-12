from __future__ import annotations

import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication

from isharescreen.gui.native_connect import _form_values
from isharescreen.gui.native_connect import ConnectWindow


def test_form_values_turn_auto_resolution_into_dynamic_native_session():
    values = _form_values(
        host=" mac.local ", user=" vincent ", password="secret",
        resolution="auto", scale="2.0", decoder="auto", audio=True,
        curtain=True, hdr=False, session_mode="auto",
    )

    assert values.host == "mac.local"
    assert values.user == "vincent"
    assert values.password == "secret"
    assert values.advertise == "auto"
    assert values.dynamic_resolution is True
    assert values.frontend == "desktop"
    assert values.share_console is False and values.alt_session is False


def test_form_values_preserve_fixed_scale_decoder_and_session_mode():
    values = _form_values(
        host="mac.local", user="v", password="p", resolution="2560x1440",
        scale="1.5", decoder="qsv-hevc444", audio=False, curtain=False,
        hdr=True, session_mode="alternate",
    )

    assert values.advertise == "2560x1440"
    assert values.dynamic_resolution is False
    assert values.hidpi == "1.5"
    assert values.decoder == "qsv-hevc444"
    assert values.audio is False and values.curtain is False and values.hdr is True
    assert values.alt_session is True and values.share_console is False


def test_connect_form_inputs_share_one_aligned_field_column():
    app = QApplication.instance() or QApplication([])
    window = ConnectWindow()
    window.show()
    app.processEvents()

    host_x = window.host.mapTo(window, QPoint(0, 0)).x()
    resolution_x = window.resolution.mapTo(window, QPoint(0, 0)).x()
    assert host_x == resolution_x

    window.close()
