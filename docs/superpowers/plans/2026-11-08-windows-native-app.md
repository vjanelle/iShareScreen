# Windows Native App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver iShareScreen as a single Windows executable with native PySide6 connect and diagnostics windows plus the existing native video viewer.

**Architecture:** On Windows, the entry point opens a PySide6 application. A session worker is launched as a hidden worker mode of the same executable, so the UI can remain responsive while the existing CLI owns the session and GLFW/wgpu viewer. The UI reads the existing loopback control stream and worker output, and exposes native actions and prompts. PyInstaller builds one windowed executable containing the runtime, Qt plugins, and native dependencies.

**Tech Stack:** Python 3.10+, PySide6/Qt Widgets, existing ControlServer TCP loopback protocol, PyInstaller one-file Windows build.

**Spec:** `docs/superpowers/specs/2026-11-08-windows-native-app-design.md`

## Global Constraints

- Target Windows first; keep platform-neutral CLI and existing frontends intact.
- Keep the single-file PyInstaller build reproducible from a documented build command/configuration in the repository.
- Include the Qt/PySide license texts and third-party notices required for the selected bundled distribution.
- Preserve unrelated user edits in `frontend/desktop/app.py`.
- Persist connection preferences but never persist passwords.
- Preserve existing CLI and headless entry points.

## Review Focus

- Frozen GUI relaunching itself must route to the worker mode without opening a second UI.
- Closing or reconnecting during startup must terminate and reap the previous worker and release its control-port sidecar.
- A worker that exits before sending a hello/snapshot must leave the UI responsive and show its diagnostic output.
- The share-console versus alternate-session decision must be answerable from a native dialog and time out to the existing share default.
- The one-file build must include PySide6 plugins, wgpu/GLFW libraries, PyAV/FFmpeg libraries, decoder sample resources, and audio dependencies.

---

### Task 1: Add Windows native UI dependency and frozen entry routing

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/isharescreen/tui/entry.py`
- Create: `src/isharescreen/gui/__init__.py` only if needed for package exports
- Create: `src/isharescreen/gui/native_entry.py`

**Interfaces:**
- `native_entry.main(argv: list[str] | None = None) -> int` creates and runs the Qt application.
- `entry.main()` routes Windows normal launches to the native UI, CLI flags to the CLI, and the private `--iss-worker` mode directly to the CLI.

- [x] Add a Windows runtime extra for `PySide6` and a build extra for `PyInstaller`; keep non-Windows installs free of a mandatory Qt dependency.
- [x] Add frozen dispatch before GUI routing so `--iss-worker` invokes the normal CLI without recursively creating another UI.
- [x] Route Windows default launches to `native_entry.main()` while retaining current non-Windows and CLI/headless behavior.
- [x] Confirm command routing with unit tests and the frozen worker help path.

### Task 2: Build native session process and control client

**Files:**
- Create: `src/isharescreen/gui/native_session.py`
- Modify: `src/isharescreen/gui/connect.py` only to extract shared launch argument construction if needed
- Modify: `src/isharescreen/cli.py` only if worker mode needs a CLI-level dispatch helper

**Interfaces:**
- `NativeSession(QObject)` exposes Qt signals for `status(dict)`, `hello(dict)`, `snapshot(dict)`, `event(dict)`, `log(str)`, and `finished(int)`.
- `NativeSession.start(values: ConnectFormValues) -> None`, `send_action(action: dict) -> None`, and `stop() -> None` manage one worker.
- `ConnectFormValues` remains the persisted, password-free form state; the password is passed to the worker through its stdin and held only in memory during launch.

- [x] Assemble the existing CLI arguments for desktop frontend, resolution/HiDPI, decoder, audio, curtain, HDR, and session mode.
- [x] Launch the current executable with `--iss-worker` when frozen, or the current Python module command during source development; use hidden-window process flags on Windows.
- [x] Connect to the worker's Windows control socket using its `.port` sidecar and parse newline-delimited hello, snapshot, and event JSON on a background thread; marshal all updates through Qt signals.
- [x] Forward `fir` and `quit` commands over the control socket; implement reconnect by stopping and reaping the worker before starting another.
- [x] Retain worker stdout/stderr in the log panel and handle early exit, failed socket connection, and missing sidecar without blocking the GUI thread.
- [x] Provide an ephemeral loopback callback for the existing `ISS_SESSION_CHOICE_URL` contract; display the share/alternate decision as a native modal and return the chosen result, defaulting to share on timeout.

### Task 3: Implement native connect window

**Files:**
- Create: `src/isharescreen/gui/native_connect.py`
- Modify: `src/isharescreen/tui/storage.py` only if the new form needs persisted fields

**Interfaces:**
- `ConnectWindow(QWidget)` loads/saves `ConnectFormValues`, emits `connect_requested(values)`, and receives available decoder labels from the existing decoder registry.
- `native_entry.main()` shows this window and owns the Qt event loop.

- [x] Create a polished Qt Widgets form for host, username, password, resolution, display scale, decoder, audio, curtain, HDR, and session selection; omit browser frontend selection.
- [x] Load/save all non-password preferences with existing storage helpers and clear password input after disconnect or reconnect.
- [x] Populate decoder choices from the existing registry, showing Auto when hardware probing fails.
- [x] Validate required host/user/password fields and present connection failures inline or in a native dialog.
- [x] Keep every form field aligned to a single control column.

### Task 4: Implement native session diagnostics and lifecycle UI

**Files:**
- Create: `src/isharescreen/gui/native_dashboard.py`
- Modify: `src/isharescreen/gui/native_connect.py`

**Interfaces:**
- `DashboardWindow(NativeSession)` presents connection status, session header, live stats, logs, and actions.
- `ConnectWindow` transfers ownership to the dashboard after a valid connect request; dashboard close calls `NativeSession.stop()` and returns to connect or exits cleanly.

- [x] Display host/frontend/session header and the useful fields already published in snapshots: stream dimensions/tiles, receive rate, loss, throughput, UDP queues, and per-tile health.
- [x] Add a bounded selectable log view and native Force IDR, Reconnect, Disconnect, and Save Bug Snapshot actions.
- [x] Add a native session-choice dialog using the callback established in Task 2.
- [x] Keep widgets responsive by updating them only from Qt's main thread; coalesce snapshot updates when needed.
- [x] Ensure app close, dashboard close, disconnect, and reconnect stop the worker and clean temporary logs/control-port artifacts.

### Task 5: Add reproducible single-file Windows build

**Files:**
- Create: `packaging/windows/isharescreen.spec`
- Create: `packaging/windows/README.md`
- Create: `packaging/windows/licenses/` notices as required by bundled dependency licenses
- Modify: `.gitignore`

**Interfaces:**
- `python -m PyInstaller packaging/windows/isharescreen.spec` produces `dist/iShareScreen.exe` from a Windows build environment.

- [x] Configure a one-file, windowed PyInstaller build with the native app entry point, Qt runtime plugins, and package data for decoder sample resources.
- [x] Collect required native dependencies for PyAV, wgpu, GLFW, sounddevice/PortAudio, and cryptography; avoid bundling development-only files.
- [x] Include Qt/PySide and third-party license texts/notices alongside the executable's embedded resources as required.
- [x] Document the supported Python version, architecture, clean build commands, output path, and known graphics/audio runtime requirements.
- [x] Keep generated `build/` and `dist/` artifacts ignored.

### Task 6: Manual Windows acceptance pass and user documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-11-08-windows-native-app-design.md` if implementation decisions materially change the design

- [x] Build the executable on Windows and confirm the output is exactly one distributable `.exe`.
- [ ] On a clean Windows account without Python installed, launch the executable and confirm no browser or console window appears. The user-provided screenshot shows the native connect window; a clean account was not available for this run.
- [ ] Verify connect form persistence, password non-persistence, native viewer launch, live diagnostics, force-IDR, reconnect, disconnect, session choice, and clean shutdown against a reachable macOS host. No Mac host or credentials were provided; worker startup and stdin were checked against a local closed port.
- [x] Verify CLI/headless flags still route to the existing CLI in a Python environment; the frozen worker help and local refusal path both ran.
- [x] Document download/use instructions and the Windows-specific one-file build process.

Task 6 is complete for the available local checks. The clean-account and live Mac session checks remain unverified because that environment was not available.

### Task 7: Add a Windows MSI installer

**Files:**
- Create: `packaging/windows/isharescreen.wixproj`
- Create: `packaging/windows/isharescreen.wxs`
- Create: `packaging/windows/build-msi.ps1`
- Modify: `packaging/windows/README.md`, `README.md`, and `.gitignore`

- [x] Add a pinned WiX project that packages the single EXE as an x64, per-user MSI with a standard install wizard, Start Menu shortcut, major upgrade support, and uninstall cleanup.
- [x] Add a PowerShell entry point that rebuilds the EXE when needed, converts the AGPL license to the installer UI format, and emits `dist/iShareScreen.msi`.
- [x] Document the .NET SDK requirement, output path, and `-SkipExeBuild` option.
- [x] Run the end-to-end EXE and MSI packaging command successfully.
