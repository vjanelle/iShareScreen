"""Native GUI credential operations with platform-specific secure storage."""
from __future__ import annotations

import sys


def read_password(host: str, username: str) -> str | None:
    if sys.platform == "win32":
        from .windows_credentials import read_password as read
        return read(host, username)
    if sys.platform.startswith("linux"):
        from ..credentials import get_password
        return get_password(host, username)
    return None


def write_password(host: str, username: str, password: str) -> None:
    if sys.platform == "win32":
        from .windows_credentials import write_password as write
        write(host, username, password)
        return
    if sys.platform.startswith("linux"):
        from ..credentials import set_password
        if set_password(host, username, password):
            return
    raise OSError("Desktop keyring unavailable, locked, or access denied; password not saved")


def delete_password(host: str, username: str) -> None:
    if sys.platform == "win32":
        from .windows_credentials import delete_password as delete
        delete(host, username)
    elif sys.platform.startswith("linux"):
        from ..credentials import delete_password as delete
        if not delete(host, username):
            raise OSError("Desktop keyring unavailable; could not confirm removal of saved password")
