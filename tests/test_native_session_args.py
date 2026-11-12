from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from isharescreen.gui.native_session import _worker_arguments, _worker_command, _take_json_lines
from isharescreen.tui.storage import ConnectFormValues


def _values(**overrides) -> ConnectFormValues:
    data = dict(
        host="mac.local", user="vincent", password="secret", advertise="1920x1080",
        audio=True, curtain=True, hdr=False, share_console=False, alt_session=False,
        frontend="desktop", dynamic_resolution=False, hidpi="2.0", decoder="auto",
    )
    data.update(overrides)
    return ConnectFormValues(**data)


def test_worker_arguments_force_native_frontend_and_keep_password_off_argv():
    args = _worker_arguments(_values(), r"C:\Temp\control", r"C:\Temp\session.log")

    assert args[:5] == ["--host", "mac.local", "-u", "vincent", "--password-stdin"]
    assert "secret" not in args
    assert "--frontend" in args and args[args.index("--frontend") + 1] == "desktop"
    assert "--control-socket" in args and args[args.index("--control-socket") + 1] == r"C:\Temp\control"
    assert "--log-file" in args and args[args.index("--log-file") + 1] == r"C:\Temp\session.log"
    assert "--advertise" in args and args[args.index("--advertise") + 1] == "1920x1080@2.0"
    assert "--no-audio" not in args and "--no-curtain" not in args


def test_worker_arguments_preserve_optional_settings():
    args = _worker_arguments(
        _values(advertise="auto", audio=False, curtain=False, hdr=True, alt_session=True, decoder="qsv-hevc444", hidpi="1.5"),
        "sock", "log",
    )

    assert args[args.index("--hidpi") + 1] == "1.5"
    assert "--no-audio" in args and "--no-curtain" in args
    assert "--hdr" in args and "--alt-session" in args
    assert args[args.index("--decoder") + 1] == "qsv-hevc444"


def test_worker_command_routes_frozen_and_source_launches():
    assert _worker_command("iShareScreen.exe", ["--host", "mac.local"], frozen=True) == [
        "iShareScreen.exe", "--iss-worker", "--host", "mac.local",
    ]
    assert _worker_command("python.exe", ["--host", "mac.local"], frozen=False) == [
        "python.exe", "-m", "isharescreen.tui.entry", "--iss-worker", "--host", "mac.local",
    ]


def test_take_json_lines_handles_fragmented_and_multiple_messages():
    messages, remaining = _take_json_lines(b'{"type":"hello"}\n{"type":"snap')
    assert messages == [{"type": "hello"}]
    assert remaining == b'{"type":"snap'

    messages, remaining = _take_json_lines(remaining + b'shot","data":{}}\n')
    assert messages == [{"type": "snapshot", "data": {}}]
    assert remaining == b""
