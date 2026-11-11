"""`iss` console-script entry. Routes between the platform GUI and CLI.

On Windows, bare `iss` opens the native PySide6 connect application. Other
platforms keep the browser connect form. CLI flags run the session directly.
"""
from __future__ import annotations

import sys


# Flags that route to `cli.py` instead of the browser connect GUI.
_CLI_ROUTING_FLAGS = {"--headless", "--help", "-h", "--version", "--list-decoders"}


def _restore_worker_stdio() -> None:
    """Reattach Python streams to inherited pipes in a frozen windowed worker."""
    if sys.platform != "win32":
        return
    import msvcrt
    import os
    import ctypes
    import io

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    get_std_handle = kernel.GetStdHandle
    get_std_handle.argtypes = [ctypes.c_ulong]
    get_std_handle.restype = ctypes.c_void_p
    for stream_name, handle_id, mode in (
        ("stdin", -10, "rb"), ("stdout", -11, "wb"), ("stderr", -12, "wb"),
    ):
        handle = get_std_handle(ctypes.c_ulong(handle_id & 0xFFFFFFFF))
        if not handle or handle == ctypes.c_void_p(-1).value:
            continue
        try:
            fd = msvcrt.open_osfhandle(handle, os.O_BINARY)
            raw = os.fdopen(fd, mode, buffering=0)
            if stream_name == "stdin":
                stream = io.TextIOWrapper(raw, encoding="utf-8", errors="replace")
            else:
                stream = io.TextIOWrapper(raw, encoding="utf-8", errors="replace", write_through=True)
            setattr(sys, stream_name, stream)
        except OSError:
            continue


def main() -> int:
    argv = sys.argv[1:]
    if "--iss-worker" in argv:
        worker_argv = [arg for arg in argv if arg != "--iss-worker"]
        if getattr(sys, "frozen", False):
            _restore_worker_stdio()
        from isharescreen.cli import main as cli_main
        return cli_main(worker_argv)
    if "--tui" in argv:
        print("iss: the terminal TUI has been removed; opening the desktop "
              "connect UI instead.", file=sys.stderr)
    # A connection / session on the command line (`--host …`), or the
    # script/help flags, run the cli directly with no GUI — this is also how
    # the GUI form launches the actual session under the hood.
    if "--host" in argv or any(a in _CLI_ROUTING_FLAGS for a in argv):
        from isharescreen.cli import main as cli_main
        return cli_main()
    # Default: native Windows UI; the browser controller remains available elsewhere.
    if sys.platform == "win32":
        from isharescreen.gui.native_entry import main as native_main
        return native_main()
    from isharescreen.gui.connect import main as gui_main
    return gui_main()


if __name__ == "__main__":
    raise SystemExit(main())
