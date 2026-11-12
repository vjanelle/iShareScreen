# Linux AppImage Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task. The user authorized execution.

**Goal:** Ship a standalone Linux viewer AppImage with secure desktop credential storage.

**Architecture:** Freeze the existing entry point using PyInstaller, wrap it in an AppDir, and build using appimagetool. Keep credential operations behind a small Linux-only module selecting trusted keyring backends.

**Tech Stack:** Python, keyring, SecretStorage, dbus-python, PyInstaller, appimagetool.

**Spec:** docs/superpowers/specs/2026-11-12-linux-appimage-design.md

## Global Constraints

- Linux viewer only; existing Mac host protocol is unchanged.
- Initial distribution: x86_64; CI build baseline Ubuntu 22.04.
- Never persist passwords in JSON, argv, logs, or HTML; no plaintext fallback.
- Host supplies browser, graphics drivers, D-Bus and keyring services.
- No publishing or remote changes.

## Review Focus

- Missing or locked keyrings must allow manually supplied credentials.
- Host/user identity changes must never retrieve another identity's password.
- Frozen children must launch the bundled CLI without recursion.
- External browser and clipboard tools must retain host library paths.
- Extracted AppImage must work away from the source checkout.

### Task 1: Secure Linux credential operations

**Files:** Create `src/isharescreen/credentials.py`, `tests/test_credentials.py`; modify `pyproject.toml`.

**Interfaces:** `get_password(host, user) -> str | None`, `set_password(host, user, password) -> bool`, `delete_password(host, user) -> bool`.

- [x] Write failing tests for identity isolation, unavailable backends, deletion, exception redaction, and secure backend selection.
- [x] Run the new tests; verify the feature is missing.
- [x] Implement explicit Secret Service/KWallet backend selection, with optional dependency imports and safe failure.
- [x] Install Linux dependencies, inspect actual backend classes, and pass the tests.

### Task 2: Form integration and frozen launch

**Files:** Modify `gui/connect.py`, `tui/storage.py`; create `runtime.py`, `tests/test_connect_credentials.py`, `tests/test_runtime.py`.

**Interfaces:** `session_command() -> list[str]` returns interpreter/module in source mode and executable in frozen mode. `host_environment() -> dict[str, str]` restores original host library paths.

- [x] Write failing tests for remember/forget, empty-password keyring lookup, unavailable storage, no rendered/persisted secrets, frozen child routing, and host environment restoration.
- [x] Run tests to verify expected failures.
- [x] Integrate remember/forget controls; persist nonsecret form settings and keep saved secrets server-side.
- [x] Use the bundled executable for session launch and restore host paths for external commands and browser launch.
- [x] Run targeted tests and the full suite.

### Task 3: AppImage packaging and verification

**Files:** Create `packaging/linux/` build script, PyInstaller spec, entry point, desktop file, icon and build requirements; `.github/workflows/appimage.yml`; update README and gitignore.

**Interfaces:** `packaging/linux/build.sh` produces `dist/iShareScreen-<version>-x86_64.AppImage`; optional `APPIMAGETOOL` supplies a local tool.

- [x] Add pinned packaging dependencies, dependency collection, bundled PortAudio, AppDir assets, and an executable build script with clear prerequisite checks.
- [x] Add Ubuntu 22.04 CI artifact build and extracted smoke checks; document runtime requirements and keyring behavior.
- [x] Build locally, run the artifact outside the checkout without PYTHONPATH, and verify version/help/decoder enumeration/assets.
- [x] Run the full suite and a fresh code review; fix material findings and report integration checks unavailable in this environment.

## Execution record

- Ruling: Execute inline in the provided workspace; the user explicitly requested execution and sandbox metadata is read-only. No additional worktree/plan approval round.
- Ruling: Build local artifact against the available host when no container runtime exists; document its actual glibc baseline. CI provides the Ubuntu 22.04 release baseline.
- Task 1 complete: 5 credential tests pass. Baseline suite: 85 passed before implementation.
- Task 2 complete: credential/form/runtime suite passes; bundled PortAudio discovery tested without a host PortAudio install.
- Ruling: User raised Vulkan/PyAV support during implementation. Add Vulkan to HEVC candidates and require `is_hwaccel` in the real-frame capability probe. Reproduced PyAV silently ignoring unavailable VAAPI despite disabled fallback; regression tests fail before fix and pass after. Installed PyAV wheel lacks VAAPI/Vulkan backends, so no working Vulkan decode is claimed for this artifact.
- Review: fresh reviewer found no important issues in AppImage/keyring changes; hardware-probe additions need final review.
- Task 3 complete: AppImage build succeeds; SHA-256 verifies. Extracted artifact runs version/help/decoder listing and serves GUI/Forget outside checkout. Isolated real GNOME Secret Service save/read/delete passes. All 102 tests pass. Fresh final review found no important regressions in hardware-probe/PortAudio additions.
- Validation limits: local artifact built on Ubuntu 26.04, glibc 2.43. Ubuntu 22.04 CI build is configured but not executed locally. Interactive KDE unlock, a live Mac connection, GPU Vulkan decode, and actual audio playback are unverified. A source-process emulation of bundled sounddevice initialization timed out in the restricted environment and was stopped; this was not an AppImage playback test.
