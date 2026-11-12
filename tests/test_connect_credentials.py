from isharescreen.gui import connect as C
from isharescreen.tui import storage as S
import pytest


@pytest.fixture(autouse=True)
def linux_form(monkeypatch):
    monkeypatch.setattr(C.sys, "platform", "linux")


def test_blank_password_resolves_saved_identity_and_forgets_when_unchecked(monkeypatch):
    saved = {("mac", "alice"): "saved-secret", ("other", "alice"): "other-secret"}
    monkeypatch.setattr(C.credentials, "get_password", lambda h, u: saved.get((h, u)))
    monkeypatch.setattr(C.credentials, "delete_password", lambda h, u: saved.pop((h, u), None) is not None)
    values = {"host": "mac", "user": "alice", "password": ""}
    assert C._prepare_credentials(values) == "saved-secret"
    assert ("mac", "alice") not in saved
    assert saved["other", "alice"] == "other-secret"


def test_supplied_password_works_when_keyring_unavailable(monkeypatch):
    monkeypatch.setattr(C.credentials, "set_password", lambda *args: False)
    messages = []
    monkeypatch.setattr(C, "_emit", lambda kind, payload: messages.append(payload))
    values = {"host": "mac", "user": "alice", "password": "manual-secret", "remember_password": "on"}
    assert C._prepare_credentials(values) == "manual-secret"
    assert any("not saved" in str(x) for x in messages)
    assert "manual-secret" not in str(messages)


def test_remember_stores_password_and_never_persists_it_in_form_state(monkeypatch, tmp_path):
    stored = {}
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    monkeypatch.setattr(C.credentials, "set_password", lambda h, u, p: stored.update({(h, u): p}) or True)
    values = {"host": "mac", "user": "alice", "password": "secret", "remember_password": "on"}
    assert C._prepare_credentials(values) == "secret"
    C._save_form(values)
    assert stored == {("mac", "alice"): "secret"}
    assert "secret" not in S._last_path().read_text()
    last = S.load_last()
    assert last.password == ""
    assert last.remember_password


def test_render_never_retrieves_or_embeds_saved_password(monkeypatch):
    def forbidden(*args):
        raise AssertionError("page render must not retrieve a password")
    monkeypatch.setattr(C.credentials, "get_password", forbidden)
    monkeypatch.setattr(C, "_decoder_options_html", lambda: "")
    monkeypatch.setattr(C, "load_last", lambda: None)
    page = C._form_page().decode()
    assert 'name="remember_password"' in page
    assert 'formaction="/forget"' in page
    assert 'name="password"' in page


def test_forget_only_deletes_submitted_identity(monkeypatch):
    saved = {("mac", "alice"): "secret", ("other", "alice"): "other"}
    monkeypatch.setattr(C.credentials, "delete_password", lambda h, u: saved.pop((h, u), None) is not None)
    assert C._forget_credentials({"host": " mac ", "user": " alice "})
    assert saved == {("other", "alice"): "other"}
