UV ?= uv
PREFIX ?= $(HOME)/.local

.PHONY: help setup install test dist appimage msi check-appimage-deps

APPIMAGE_APT_PACKAGES = build-essential pkg-config libdbus-1-dev libglib2.0-dev \
	libportaudio2 curl libxcb-cursor0 libxcb-icccm4 libxcb-keysyms1 \
	libxcb-shape0 libxcb-xinerama0 libxcb-xkb1 libxkbcommon-x11-0 \
	libegl1 libgl1 libfontconfig1 libwayland-client0 libwayland-cursor0 \
	libwayland-egl1 libxkbcommon0

help:
	@printf '%s\n' \
		'make setup     Sync the uv environment with test dependencies' \
		'make install   Build and install the AppImage to $(PREFIX)/bin' \
		'make test      Run the test suite' \
		'make dist      Build Python distributions and the native platform package' \
		'make appimage  Build the Linux AppImage' \
		'make msi       Build the Windows EXE and MSI' \
		'Run make setup first; see README.md for AppImage build dependencies'

setup:
	$(UV) sync --extra test

install: appimage
	@version=$$($(UV) run --no-sync python -c 'from isharescreen import __version__; print(__version__)'); \
		install -D -m 755 "dist/iShareScreen-$$version-$$(uname -m).AppImage" "$(PREFIX)/bin/iss"
	install -D -m 644 packaging/linux/isharescreen.desktop "$(PREFIX)/share/applications/isharescreen.desktop"
	install -D -m 644 packaging/linux/isharescreen.svg "$(PREFIX)/share/icons/hicolor/scalable/apps/isharescreen.svg"
	@if command -v update-desktop-database >/dev/null 2>&1; then update-desktop-database "$(PREFIX)/share/applications"; fi

test:
	QT_QPA_PLATFORM=$${QT_QPA_PLATFORM:-offscreen} $(UV) run --no-sync python -m pytest

ifeq ($(OS),Windows_NT)
dist:
else ifeq ($(shell uname -s),Linux)
dist: check-appimage-deps
else
dist:
endif
	$(UV) build
ifeq ($(OS),Windows_NT)
	$(MAKE) msi
else ifeq ($(shell uname -s),Linux)
	$(MAKE) appimage
endif

check-appimage-deps:
	@if command -v dpkg-query >/dev/null 2>&1; then \
		missing=''; \
		for package in $(APPIMAGE_APT_PACKAGES); do \
			if [ "$$package" = libportaudio2 ] && [ -n "$$ISS_PORTAUDIO_LIBRARY" ] && [ -f "$$ISS_PORTAUDIO_LIBRARY" ]; then continue; fi; \
			if [ "$$(dpkg-query -W -f='$${Status}' "$$package" 2>/dev/null)" != 'install ok installed' ]; then missing="$$missing $$package"; fi; \
		done; \
		if [ -n "$$missing" ]; then \
			printf 'Missing AppImage build packages:%s\nInstall them with: sudo apt install%s\n' "$$missing" "$$missing" >&2; \
			exit 1; \
		fi; \
	else \
		printf '%s\n' 'Cannot check system packages automatically; see README.md for AppImage build dependencies.' >&2; \
	fi
	@$(UV) run --no-sync python -c 'import PyInstaller, isharescreen, dbus, secretstorage, keyring; from PySide6 import QtWidgets' || \
		{ printf '%s\n' 'Python build dependency check failed; see README.md for setup instructions.' >&2; exit 1; }

appimage: check-appimage-deps
	$(UV) run --no-sync packaging/linux/build.sh

msi:
	powershell -NoProfile -ExecutionPolicy Bypass -File packaging/windows/build-msi.ps1
