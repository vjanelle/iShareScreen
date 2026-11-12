"""Entry-point routing tests for native Windows and CLI worker modes."""
from __future__ import annotations

import sys
from types import ModuleType

from isharescreen.tui import entry


def _stub(module_name: str, function_name: str, result: int, calls: list) -> ModuleType:
    module = ModuleType(module_name)

    def main(argv=None):
        calls.append(argv)
        return result

    setattr(module, function_name, main)
    return module


def test_windows_default_routes_to_native_ui(monkeypatch):
    calls = []
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(sys, "argv", ["iss.exe"])
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    monkeypatch.setitem(
        sys.modules,
        "isharescreen.gui.native_entry",
        _stub("isharescreen.gui.native_entry", "main", 17, calls),
    )
    monkeypatch.setitem(
        sys.modules,
        "isharescreen.gui.connect",
        _stub("isharescreen.gui.connect", "main", 19, []),
    )

    assert entry.main() == 17
    assert calls == [None]


def test_worker_mode_routes_to_cli_and_removes_private_flag(monkeypatch):
    calls = []
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(sys, "argv", ["iss.exe", "--iss-worker", "--host", "mac.local"])
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(entry, "_restore_worker_stdio", lambda: None, raising=False)
    monkeypatch.setitem(
        sys.modules,
        "isharescreen.cli",
        _stub("isharescreen.cli", "main", 23, calls),
    )

    assert entry.main() == 23
    assert calls == [["--host", "mac.local"]]


def test_headless_cli_flags_still_bypass_native_ui(monkeypatch):
    calls = []
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(sys, "argv", ["iss.exe", "--headless"])
    monkeypatch.setitem(
        sys.modules,
        "isharescreen.cli",
        _stub("isharescreen.cli", "main", 29, calls),
    )

    assert entry.main() == 29
    assert calls == [None]
