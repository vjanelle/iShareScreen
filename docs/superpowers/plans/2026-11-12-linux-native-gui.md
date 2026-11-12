# Linux Native GUI Integration Plan

> Execute inline using superpowers:executing-plans. The user requested merging and adapting the existing GUI; preserve the authorized AppImage/keyring work.

**Goal:** Make the existing PySide6 Windows GUI the default Linux AppImage interface.

**Architecture:** Reuse the connection window, dashboard and worker controller from origin/main. Add a platform credential adapter and POSIX control transport; keep Windows behavior. Package Qt's Linux platform plugins and expose the previous browser controller with `--browser-ui`.

**Spec:** User's explicit request to merge and adapt the native Windows GUI, plus the existing Linux AppImage/keyring design.

## Tasks

- [x] Merge origin/main and resolve state-field conflict, keeping both preference fields. Baseline: 174 tests and 11 subtests pass with Qt installed.
- [x] Add failing tests for Linux entry routing, explicit browser UI, desktop keyring adapter, credential identity isolation, forget behavior, and POSIX control socket transport.
- [x] Adapt native form/controller to Linux credentials without Windows APIs, preserve opt-in saving and no plaintext fallback, and keep keyring I/O off the Qt event loop.
- [x] Route Linux to native GUI; retain CLI/worker paths. Connect native diagnostics over AF_UNIX on Linux and the existing TCP sidecar on Windows.
- [x] Bundle PySide6 plugins/dependencies/licenses, protect external helpers from Qt's private plugin paths, update CI smoke checks and documentation.
- [x] Run the full offscreen Qt suite, build the AppImage, smoke-test actual native startup and worker dispatch, review, and commit.

## Review focus

- Late credential reads must not overwrite typed passwords or a changed identity.
- Missing/locked keyrings must not freeze the form or stop manually entered connections.
- Worker processes must inherit source/frozen routing without starting another GUI.
- Qt xcb/Wayland plugins must load from the bundle; host tools must not inherit incompatible Qt paths.
- Native control transport must use the same Unix socket as the Linux worker.

## Execution record

- Merge commit: 9129760. No remote push authorized.

- Native adaptation: Linux defaults to the existing Qt form/dashboard, with explicit --browser-ui retained. Credentials are handled by the secure platform adapter; read/save/forget run outside Qt's event loop.
- Validation: 182 tests and 11 subtests passed. Real AF_UNIX hello/snapshot/command round trip passed. The Qt form restored and forgot a test credential against an isolated GNOME Secret Service.
- AppImage validation: source-independent offscreen native startup, worker routing, help, Qt plugins and HEVC samples passed. Visible native startup passed on X11 (xcb) and Wayland. Explicit browser controller smoke passed. Checksum verifies.
- Test isolation: one Qt test run crashed while a form test read the user's real saved identity and created background keyring work around QApplication destruction. Form tests now avoid user settings, and a session Qt application remains alive while native tests exchange signals. Subsequent complete suites passed.
- Independent review: no important findings in Linux native changes.
- Limits: local AppImage still targets the build host's glibc 2.43. Ubuntu 22.04 CI is configured but has not run here; real KDE unlock prompts and a live Mac session remain manual integration checks.
