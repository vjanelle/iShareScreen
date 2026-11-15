# Repository Guidelines

## Project Structure & Module Organization

The Python package lives in `src/isharescreen/`. `proxy/` implements the screen-sharing protocol, session control, and media handling; `frontend/` contains desktop and WebTransport viewers; `gui/` and `tui/` provide application interfaces. Tests are in `tests/`, with shared fixtures in `tests/conftest.py`. Protocol and media notes are in `docs/`; platform packaging is in `packaging/linux/` and `packaging/windows/`. Supporting utilities live in `tools/`.

## Build, Test, and Development Commands

- `make install` syncs the uv environment with the project and test dependencies.
- `make test` runs pytest with Qt's offscreen platform by default. Set `QT_QPA_PLATFORM` explicitly to override it.
- `uv run --no-sync iss` starts the locally installed application; use `--help` for options.
- `make appimage` runs the Linux AppImage build. Install the system and build dependencies described in the README first; Ubuntu 22.04 x86_64 is the supported build baseline.
- On Windows, follow `packaging/windows/README.md` to build the PyInstaller executable and MSI.

## Coding Style & Naming Conventions

Follow the surrounding Python code: four-space indentation, `snake_case` for modules, functions, and variables, and `PascalCase` for classes. Keep platform-specific behavior isolated and document non-obvious protocol or media decisions. No repository-wide formatter or linter is configured in `pyproject.toml`.

## Testing Guidelines

Tests use pytest and are discovered under `tests/`. Name files `test_*.py` and test functions `test_*`; place shared fixtures in `conftest.py` where appropriate. Run `make test` before submitting changes, or target a module with `uv run --no-sync python -m pytest tests/test_runtime.py`. Add focused regression tests for behavior changes. The project does not declare a coverage threshold; tests should avoid requiring a remote Mac or network when practical.

## Commit & Pull Request Guidelines

Recent commits use short, imperative subjects with prefixes such as `fix:`, `feat:`, and `merge:`. Keep each commit focused. Pull requests should explain the user-visible change and motivation, link relevant issues, and report the tests run. Include screenshots for visible interface changes and identify platform-specific build or runtime limitations.

## Security & Configuration

Never commit credentials or captured secrets. Preserve the existing desktop keyring behavior and avoid plaintext password storage. Consult the README for platform dependencies and firewall requirements.
