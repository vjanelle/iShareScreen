# Windows native app design

## Intent

Package iShareScreen for Windows as a single executable that users can launch
without installing Python. The app should use native windows throughout instead
of opening a browser for its connect form or session controls.

## Goals

- Provide a native Windows connect window and session status/diagnostics window.
- Reuse the existing native wgpu/GLFW video viewer.
- Produce a single-file Windows executable with PyInstaller.
- Preserve saved connection preferences; never save passwords.
- Keep CLI/headless use available for developers and scripts.

## Non-goals

- A traditional installer, auto-updater, code signing, or macOS/Linux packaging.
- Replacing the existing video renderer or changing the streaming protocol.
- Requiring a browser or WebView runtime in the Windows user flow.

## Current behavior and constraints

The `iss` entry point opens `isharescreen.gui.connect`, a stdlib HTTP server
whose connect form and live diagnostics are rendered in the user's browser. It
starts a second Python process for each session. The session CLI already has a
`--frontend desktop` option that opens the native wgpu viewer. Its default is
the browser frontend. The current form stores preferences in `%LOCALAPPDATA%`
and intentionally omits passwords. PyInstaller must collect the Python
dependencies, native DLLs, and package resources needed by wgpu, GLFW, PyAV,
and the media decoder. The Windows build remains a single `.exe`.

## Approaches

1. **PySide6/Qt controller plus existing desktop viewer (chosen).** Use Qt
   Widgets for connect and diagnostics windows, and the existing native desktop
   viewer for video. Qt provides a richer, more polished desktop UI than the
   standard-library toolkit, at the cost of a larger dependency and packaging
   surface. PyInstaller can bundle the Qt runtime and plugins into the single
   executable; build and distribution must account for Qt's LGPL/GPL or
   commercial licensing terms. The controller must coordinate session
   lifecycle and stream metrics without relying on a browser dashboard.
2. **Tkinter/ttk controller plus existing desktop viewer.** Avoids another
   large runtime and has standard-library availability, but its visual style
   is less polished for the intended application.
3. **Keep the browser controller and only use the native video window.** This
   works with today's frontend option but does not meet the fully native UI
   requirement.

## Proposed behavior

- Launching the executable opens a native connect window.
- The form retains the current host, username, password, resolution, audio,
  curtain, session, decoder, and frontend-relevant choices. Since the product
  is fully native on Windows, users do not choose a browser video frontend.
- Connecting opens the existing desktop video viewer and a native session
  window for connection state, diagnostics/log output, reconnect, disconnect,
  force-IDR, session-choice prompts, and bug-report snapshot actions supported
  by the current dashboard.
- Reconnect reuses the last non-password settings. Password remains in memory
  only for the current launch/session.
- Closing the controller cleanly disconnects the active session and shuts down
  its worker.
- Existing CLI and headless entry points continue to work.

## Constraints and builder calls

- Target Windows first; keep platform-neutral CLI and existing frontends intact.
- Keep the single-file PyInstaller build reproducible from a documented build
  command/configuration in the repository.
- Include the Qt/PySide license texts and third-party notices required for the
  selected bundled distribution.
- The builder chooses the safest frozen-process/session lifecycle design after
  checking GLFW/wgpu thread requirements, stdin/stdout behavior, and the
  existing control-socket protocol. It must avoid recursively launching the
  GUI entry point when the frozen executable is used for a session worker.
- Include required package data and native DLLs, and provide useful startup
  errors when a GPU, audio device, or decoder is unavailable.
- Preserve unrelated user edits in `frontend/desktop/app.py`.

## Acceptance

- The Windows executable starts a native connect window without opening a
  browser.
- A successful session presents video in the existing native viewer and
  status/diagnostic controls in native windows.
- Connect, reconnect, disconnect, force-IDR, session-choice, and close/shutdown
  flows behave correctly.
- The distributable is one `.exe` that launches on a clean Windows machine
  without a separately installed Python runtime.
- CLI/headless behavior and password non-persistence remain intact.
