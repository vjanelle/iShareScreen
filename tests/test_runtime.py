import os
import sys
import ctypes.util

from isharescreen import runtime as R


def test_source_and_frozen_session_commands(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert R.session_command() == [sys.executable, "-m", "isharescreen.cli"]
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", "/tmp/iss bundle/iss")
    assert R.session_command() == ["/tmp/iss bundle/iss"]


def test_frozen_entry_restores_host_library_environment(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setenv("LD_LIBRARY_PATH", "/tmp/frozen/_internal")
    monkeypatch.setenv("LD_LIBRARY_PATH_ORIG", "/host/libs")
    R.configure_environment()
    assert os.environ["LD_LIBRARY_PATH"] == "/host/libs"
    monkeypatch.delenv("LD_LIBRARY_PATH_ORIG")
    monkeypatch.setenv("LD_LIBRARY_PATH", "/tmp/frozen/_internal")
    R.configure_environment()
    assert "LD_LIBRARY_PATH" not in os.environ


def test_source_environment_is_unchanged(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.setenv("LD_LIBRARY_PATH", "/custom/libs")
    R.configure_environment()
    assert os.environ["LD_LIBRARY_PATH"] == "/custom/libs"


def test_bundled_portaudio_is_found_without_a_system_install(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    monkeypatch.setattr(ctypes.util, "find_library", lambda name: None)
    (tmp_path / "libportaudio.so.2").touch()
    R.configure_environment()
    assert ctypes.util.find_library("portaudio") == str(tmp_path / "libportaudio.so.2")
    assert ctypes.util.find_library("other") is None


def test_frozen_qt_paths_do_not_leak_to_host_helpers(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    monkeypatch.setenv("QT_PLUGIN_PATH", str(tmp_path / "PySide6/Qt/plugins"))
    monkeypatch.setenv("QML2_IMPORT_PATH", str(tmp_path / "PySide6/Qt/qml"))
    monkeypatch.setenv("QT_QPA_PLATFORM_PLUGIN_PATH", "/host/qt/plugins")
    R.configure_environment()
    assert "QT_PLUGIN_PATH" not in os.environ
    assert "QML2_IMPORT_PATH" not in os.environ
    assert os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] == "/host/qt/plugins"
