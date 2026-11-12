"""Linux adaptation of the existing Qt form and worker transport."""
import socket
import sys
import threading

import pytest

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest

from isharescreen.gui import credential_store as store
from isharescreen.gui import native_session as session
from isharescreen.gui.native_connect import ConnectWindow


def test_linux_credentials_use_desktop_keyring_and_propagate_write_failure(monkeypatch):
    from isharescreen import credentials
    monkeypatch.setattr(sys, "platform", "linux")
    values = {}
    monkeypatch.setattr(credentials, "get_password", lambda h, u: values.get((h, u)))
    monkeypatch.setattr(credentials, "set_password", lambda h, u, p: values.update({(h, u): p}) or True)
    monkeypatch.setattr(credentials, "delete_password", lambda h, u: values.pop((h, u), None) is not None)
    store.write_password("mac", "alice", "secret")
    assert store.read_password("mac", "alice") == "secret"
    assert store.read_password("other", "alice") is None
    store.delete_password("mac", "alice")
    assert store.read_password("mac", "alice") is None
    monkeypatch.setattr(credentials, "set_password", lambda *args: False)
    with pytest.raises(OSError, match="keyring"):
        store.write_password("mac", "alice", "secret")


def test_linux_control_connects_to_unix_socket(monkeypatch):
    calls = []
    class Connection:
        def settimeout(self, timeout):
            pass
        def connect(self, address):
            calls.append(address)
        def close(self):
            pass
    conn = Connection()
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(session.socket, "socket", lambda family, kind: (
        calls.append((family, kind)) or conn))
    assert session._connect_control("/tmp/iss-test/control") is conn
    assert calls == [(socket.AF_UNIX, socket.SOCK_STREAM), "/tmp/iss-test/control"]


def test_linux_form_forget_uses_entered_identity(monkeypatch):
    from isharescreen.gui import native_connect as form
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(form, "load_last", lambda: None)
    monkeypatch.setattr(ConnectWindow, "_populate_decoders", lambda self: self.decoder.addItem("Auto", "auto"))
    entries = {("mac", "alice"): "secret", ("other", "alice"): "other"}
    monkeypatch.setattr(store, "delete_password", lambda h, u: entries.pop((h, u), None))
    app = QApplication.instance() or QApplication([])
    window = ConnectWindow()
    window.host.setText(" mac ")
    window.user.setText(" alice ")
    window.password.setText("secret")
    window.save_password.setChecked(True)
    assert "keyring" in window.save_password.text().lower()
    window._forget_saved_password()
    for _ in range(100):
        app.processEvents()
        if window.forget_password.isEnabled():
            break
        QTest.qWait(10)
    assert entries == {("other", "alice"): "other"}
    assert window.password.text() == ""
    assert not window.save_password.isChecked()
    window.close()


def test_forget_keeps_the_form_responsive_while_keyring_waits(monkeypatch):
    from isharescreen.gui import native_connect as form
    monkeypatch.setattr(form, "load_last", lambda: None)
    monkeypatch.setattr(ConnectWindow, "_populate_decoders", lambda self: self.decoder.addItem("Auto", "auto"))
    release, done = threading.Event(), threading.Event()
    def delayed_delete(*args):
        release.wait(timeout=1)
        done.set()
    monkeypatch.setattr(store, "delete_password", delayed_delete)
    app = QApplication.instance() or QApplication([])
    window = ConnectWindow()
    window.host.setText("mac")
    window.user.setText("alice")
    try:
        window._forget_saved_password()
        assert not done.is_set(), "keyring I/O blocked the GUI thread"
    finally:
        release.set()
        for _ in range(100):
            app.processEvents()
            if done.is_set() and window.forget_password.isEnabled():
                break
            QTest.qWait(10)
        window.close()


def test_late_keyring_result_cannot_replace_typed_or_different_identity(monkeypatch):
    from isharescreen.gui import native_connect as form
    monkeypatch.setattr(form, "load_last", lambda: None)
    monkeypatch.setattr(ConnectWindow, "_populate_decoders", lambda self: self.decoder.addItem("Auto", "auto"))
    app = QApplication.instance() or QApplication([])
    window = ConnectWindow()
    window.host.setText("mac")
    window.user.setText("alice")
    window._credential_identity = ("mac", "alice")
    window._credential_generation = 5
    window.password.setText("typed")
    window._apply_saved_password(("mac", "alice"), 5, "saved")
    assert window.password.text() == "typed"
    window.password.clear()
    window.host.setText("other")
    window._apply_saved_password(("mac", "alice"), 5, "saved")
    assert window.password.text() == ""
    window.close()
