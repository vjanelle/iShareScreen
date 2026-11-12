# Display Scale and Password Storage Implementation Plan

> **For agentic workers:** Inline implementation plan for the approved design.

**Goal:** Default new connections to 100% display scale and let the native Windows form save passwords in Windows Credential Manager.

**Architecture:** Keep connection preferences in the existing JSON storage, but isolate password read/write/delete behind a Windows-only credential helper. The native form retrieves matching credentials and saves or deletes them based on an opt-in checkbox; the browser form only changes its scale default.

**Tech Stack:** Python, ctypes Win32 Credential Manager API, PySide6.

**Spec:** `docs/superpowers/specs/2026-11-09-display-scale-and-password-storage-design.md`

## Global Constraints

- Never persist a password in `last.json`.
- Use Windows Credential Manager, keyed by host and username.
- New forms select 100%, preserving saved scale preferences.
- Do not add SSH authentication.

## Review Focus

- A host or username change must not reuse another account's saved password.
- Unchecking password saving must remove a previously stored matching credential.
- Credential Manager errors must not prevent connecting with a manually entered password.
- Existing saved display scale must remain selected.
- Non-Windows imports must not fail because Win32 APIs are unavailable.

## Files

- Create `src/isharescreen/gui/windows_credentials.py` for Win32 read/write/delete helpers.
- Modify `src/isharescreen/gui/native_connect.py` for matching credential lookup and opt-in UI.
- Modify `src/isharescreen/gui/native_session.py` to persist or remove the selected credential on connect.
- Modify `src/isharescreen/gui/connect.py` for the browser form's fresh default scale.

## Tasks

### Task 1: Windows Credential Manager helper

Implement `read_password(host: str, username: str) -> str | None`, `write_password(host: str, username: str, password: str) -> None`, and `delete_password(host: str, username: str) -> None`. Use generic credentials with a stable SHA-256 target derived from normalized host and username. Keep Win32 imports lazy and raise `OSError` on API failures.

### Task 2: Native form and session integration

Add `save_password: bool = False` to `ConnectFormValues`. Add an opt-in checkbox. Prefill from Credential Manager for the current host and username; refresh on editing completion and clear stale password contents when the identity changes. On connect, write when checked and delete the matching entry when unchecked. A credential API failure must be logged and must not block the connection. Change fresh native scale selection and fallback from 200% to 100%, while retaining saved non-auto scales.

### Task 3: Browser scale default

Change the browser form's selected scale and missing-value fallback from 200% to 100%.

## Execution notes

The workspace has pre-existing uncommitted changes; preserve them. Do not run the project test suite unless requested. Review the final diff for scope and ensure no password field is added to JSON persistence.
