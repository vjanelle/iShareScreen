# Display scale and password storage

## Intent

Make new connections render the Mac UI at 100% by default and let users save
the Mac account password securely for later connections.

## Scope and constraints

- Apply the 100% default to both the native Windows form and browser connect
  form, without overriding an explicitly saved display scale.
- Save passwords only when the user opts in. Store them in Windows Credential
  Manager, keyed by host and username; never write them to `last.json`.
- Restore a saved password for the matching host and username, and allow the
  user to stop saving it.
- SSH key authentication is out of scope: there is no key material, and the
  screen-sharing protocol expects account-password authentication.

## Approaches

- Use Windows Credential Manager through a small direct Win32 wrapper. This
  targets the app's Windows native UI without adding a runtime dependency.
- Add a cross-platform credential library. This is simpler across operating
  systems, but the requested Windows-only integration does not need it.

Use the direct Win32 wrapper, with graceful UI behavior if credential storage
is unavailable. Keep the browser connect form's password handling unchanged;
it runs separately and is not the Windows native credential UI.

## Success criteria

- Fresh native and browser connect forms select 100%; saved scale preferences
  remain effective.
- The native form can save, retrieve, and remove credentials through Windows
  Credential Manager without including the password in JSON settings.
- No SSH authentication mode is added.
