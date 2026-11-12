# Standalone Linux AppImage

## Intent

Deliver iShareScreen as a standalone Linux viewer for the existing macOS
Screen Sharing host. The user selected AppImage over a portable tarball.
Linux screen sharing server support is outside this work.

## Distribution

Use PyInstaller in directory mode to bundle Python, application code,
browser assets, Python dependencies, and their required shared libraries.
Wrap the bundle in an AppDir with AppRun, desktop metadata, and an SVG icon,
then produce a type 2 AppImage with appimagetool. Include build instructions
and a repeatable Linux build script, plus CI to produce the artifact.

The proposed initial target is x86_64, built on Ubuntu 22.04 for its glibc
baseline. Architecture and baseline are builder proposals, not user choices.
The host supplies its kernel, graphics drivers, graphical session, D-Bus,
keyring daemon, and browser for the existing browser control interface.
The native viewer remains available. Include PortAudio; document optional
AAC decoder availability and clipboard utilities honestly rather than claim
every system service is bundled. Do not bundle a browser or GPU drivers.

Fix session subprocess launch for frozen executables: re-enter the bundled
entry point with CLI arguments rather than execute Python's -m syntax.
Retain source-install behavior. Ensure bundled runtime library paths do not
break external host utilities or browser launch.

## Credential storage

Add an explicit remember-password checkbox and a way to forget a saved
credential in the existing browser connect form. Store secrets by host and
username using desktop credential services, never JSON, argv, logs, or HTML.
An empty password on connect may resolve a saved credential for the submitted
host/user pair. Do not send saved passwords back to the browser.

Use the maintained Python keyring package with explicitly selected secure
Linux backends: GNOME Secret Service and KDE Wallet. Include their runtime
dependencies in the bundle. Prefer KDE integration in a KDE session, with
Secret Service support for GNOME and modern KDE. Reject plaintext and
third-party fallback backends. Backend selection details are left to the
implementation after checking current library support.

When storage is unavailable, locked, or denied, report a clear message and
allow a connection using a manually supplied password. Never silently save
to disk. Remembering is opt-in; unchecking on a later connection removes the
saved entry for that identity. Forgetting deletes only that identity.
Keep nonsecret form settings in the existing state file and wire their save
operation into the browser GUI, which currently only loads state.
CLI password-stdin retains precedence and scripted use must not start
unlock prompts unexpectedly. CLI keyring use may be explicit if added.

## Approaches considered

* Portable tarball: simpler extraction and packaging, but the user chose
  AppImage for delivery.
* AppImage with a bundled Python environment: chosen; launch without a
  system Python or pip installation while retaining the existing app.
* Rewrite as a native Linux application: unnecessary scope and risk for
  an existing Python viewer; not proposed.

## Validation

Test credential identity isolation, secure backend selection, unavailable
or locked services, saving/deleting, and absence of passwords from persisted
settings and rendered pages. Test frozen and source session command routing.
Run the existing suite. Build the AppImage and smoke-test its version/help,
decoder enumeration, bundled assets, and launch from outside the checkout
with no source path overrides. Exercise real GNOME/KDE and remote-Mac
sessions where available; explicitly report any unavailable integration
checks. A successful unit test run alone is not proof of desktop integration.

## Remaining implementation decisions

The builder chooses exact dependency versions, PyInstaller collection hooks,
CI artifact naming, and minor UI wording. Pin build tooling and document
build prerequisites. Do not publish releases or change the remote repository
without separate user authorization.
