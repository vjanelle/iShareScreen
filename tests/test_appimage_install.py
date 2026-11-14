from pathlib import Path

from isharescreen.gui.appimage_install import install_appimage, should_offer_install


def test_install_creates_executable_and_desktop_integration(tmp_path, monkeypatch):
    home = tmp_path / 'home with spaces'
    home.mkdir()
    source = tmp_path / 'download.AppImage'
    source.write_bytes(b'appimage')
    icon = tmp_path / 'icon.svg'
    icon.write_text('<svg/>')
    monkeypatch.setenv('HOME', str(home))
    monkeypatch.setenv('XDG_DATA_HOME', str(home / '.local/share'))
    install_appimage(source, icon)
    binary = home / '.local/bin/iss'
    desktop = home / '.local/share/applications/isharescreen.desktop'
    assert binary.read_bytes() == b'appimage'
    assert binary.stat().st_mode & 0o111
    assert f'Exec="{binary}"' in desktop.read_text()
    assert f'Icon={home / ".local/share/icons/hicolor/scalable/apps/isharescreen.svg"}' in desktop.read_text()
    assert (home / '.local/share/icons/hicolor/scalable/apps/isharescreen.svg').read_text() == '<svg/>'
    assert not should_offer_install(source)


def test_offer_requires_appimage_and_no_existing_launcher(tmp_path, monkeypatch):
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.delenv('XDG_DATA_HOME', raising=False)
    assert not should_offer_install(None)
    assert should_offer_install(tmp_path / 'appimage')


def test_appimage_sets_desktop_identity_and_window_icon(tmp_path, monkeypatch, qt_application):
    from isharescreen.gui.native_entry import _configure_linux_desktop

    (tmp_path / 'isharescreen.svg').write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16"><rect width="16" height="16"/></svg>'
    )
    monkeypatch.setenv('APPDIR', str(tmp_path))
    _configure_linux_desktop(qt_application)
    assert qt_application.desktopFileName() == 'isharescreen'
    assert not qt_application.windowIcon().isNull()
