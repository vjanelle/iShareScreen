"""Credentials must stay in an explicitly trusted desktop backend."""
import logging
import sys

import pytest

from isharescreen import credentials as C


class MemoryWallet:
    def __init__(self):
        self.values = {}

    def get_password(self, service, user):
        return self.values.get((service, user))

    def set_password(self, service, user, password):
        self.values[service, user] = password

    def delete_password(self, service, user):
        del self.values[service, user]


def test_passwords_are_isolated_by_host_and_user(monkeypatch):
    wallet = MemoryWallet()
    monkeypatch.setattr(C, "_backend", lambda: wallet)
    assert C.set_password("mac.local", "alice", "secret-a")
    assert C.set_password("mac.local", "bob", "secret-b")
    assert C.set_password("other.local", "alice", "secret-c")
    assert C.get_password("mac.local", "alice") == "secret-a"
    assert C.get_password("mac.local", "bob") == "secret-b"
    assert C.get_password("other.local", "alice") == "secret-c"
    assert C.delete_password("mac.local", "alice")
    assert C.delete_password("mac.local", "alice")  # idempotent
    assert C.get_password("mac.local", "alice") is None
    assert C.get_password("mac.local", "bob") == "secret-b"


def test_unavailable_backend_never_persists_to_disk(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(C, "_backend", lambda: None)
    assert C.get_password("mac", "alice") is None
    assert not C.set_password("mac", "alice", "secret")
    assert not C.delete_password("mac", "alice")
    assert list(tmp_path.iterdir()) == []


def test_locked_backend_errors_do_not_disclose_secrets(monkeypatch, caplog):
    class Locked(MemoryWallet):
        def get_password(self, *args):
            raise RuntimeError("secret-password-from-backend")

        set_password = delete_password = get_password

    monkeypatch.setattr(C, "_backend", lambda: Locked())
    with caplog.at_level(logging.WARNING):
        assert C.get_password("mac", "alice") is None
        assert not C.set_password("mac", "alice", "top-secret")
        assert not C.delete_password("mac", "alice")
    assert "secret-password-from-backend" not in caplog.text
    assert "top-secret" not in caplog.text


def test_failed_wallet_write_is_not_reported_as_saved(monkeypatch):
    class FailedWrite(MemoryWallet):
        def set_password(self, *args):
            pass

    monkeypatch.setattr(C, "_backend", lambda: FailedWrite())
    assert not C.set_password("mac", "alice", "secret")


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux backend dependencies")
def test_only_explicit_secure_backends_are_candidates(monkeypatch):
    monkeypatch.setattr(C.sys, "platform", "linux")
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "KDE")
    monkeypatch.setenv("PYTHON_KEYRING_BACKEND", "keyrings.alt.file.PlaintextKeyring")
    candidates = C._candidates()
    assert [(c.bus_name, c.object_path) for c in candidates[:2]] == [
        ("org.kde.kwalletd6", "/modules/kwalletd6"),
        ("org.kde.kwalletd5", "/modules/kwalletd5"),
    ]
    assert candidates[-1].__module__ == "keyring.backends.SecretService"
    assert len(candidates) == 3
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "GNOME")
    assert C._candidates()[0].__module__ == "keyring.backends.SecretService"
