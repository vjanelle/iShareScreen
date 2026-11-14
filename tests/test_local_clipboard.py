import sys
from types import SimpleNamespace

from isharescreen.proxy import local_clipboard


def test_kde_wayland_uses_klipper_without_wl_clipboard(monkeypatch):
    values = []
    interface = SimpleNamespace(getClipboardContents=lambda: 'hello',
                                setClipboardContents=lambda text: values.append(text))
    bus = SimpleNamespace(get_object=lambda service, path: interface)
    monkeypatch.setitem(sys.modules, 'dbus', SimpleNamespace(SessionBus=lambda: bus, Interface=lambda obj, name: obj))
    monkeypatch.setattr(sys, 'platform', 'linux')
    monkeypatch.setenv('XDG_CURRENT_DESKTOP', 'KDE')
    monkeypatch.setenv('WAYLAND_DISPLAY', 'wayland-0')
    monkeypatch.setattr(local_clipboard.pyperclip, 'paste', lambda: (_ for _ in ()).throw(AssertionError('wl-paste called')))
    assert local_clipboard.available()
    assert local_clipboard.read_text() == 'hello'
    assert local_clipboard.push_text('world')
    assert values == ['world']


def test_kde_unavailable_does_not_fall_back_to_focus_stealing_helper(monkeypatch):
    monkeypatch.setattr(sys, 'platform', 'linux')
    monkeypatch.setenv('XDG_CURRENT_DESKTOP', 'KDE')
    monkeypatch.setenv('WAYLAND_DISPLAY', 'wayland-0')
    monkeypatch.setitem(sys.modules, 'dbus', SimpleNamespace(SessionBus=lambda: (_ for _ in ()).throw(RuntimeError('unavailable'))))
    monkeypatch.setattr(local_clipboard.pyperclip, 'paste', lambda: (_ for _ in ()).throw(AssertionError('wl-paste called')))
    assert not local_clipboard.available()
    assert local_clipboard.read_text() is None
    assert not local_clipboard.push_text('text')
