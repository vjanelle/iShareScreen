"""PyInstaller entry point; normal routing also handles frozen child sessions."""
from isharescreen.tui.entry import main

if __name__ == "__main__":
    raise SystemExit(main())
