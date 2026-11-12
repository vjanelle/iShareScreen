"""Small wrapper for Windows Credential Manager generic credentials."""
from __future__ import annotations

import ctypes
import hashlib
import sys
from ctypes import wintypes


_CRED_TYPE_GENERIC = 1
_CRED_PERSIST_LOCAL_MACHINE = 2
_ERROR_NOT_FOUND = 1168


class _Credential(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR),
        ("LastWritten", wintypes.FILETIME),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
        ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]


def _target_name(host: str, username: str) -> str:
    identity = f"{host.strip().casefold()}\0{username.strip()}".encode("utf-8")
    digest = hashlib.sha256(identity).hexdigest()
    return f"iShareScreen:{digest}"


def _api():
    if sys.platform != "win32":
        raise OSError("Windows Credential Manager is available only on Windows")
    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    advapi.CredReadW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                 ctypes.POINTER(ctypes.POINTER(_Credential))]
    advapi.CredReadW.restype = wintypes.BOOL
    advapi.CredWriteW.argtypes = [ctypes.POINTER(_Credential), wintypes.DWORD]
    advapi.CredWriteW.restype = wintypes.BOOL
    advapi.CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
    advapi.CredDeleteW.restype = wintypes.BOOL
    advapi.CredFree.argtypes = [ctypes.c_void_p]
    advapi.CredFree.restype = None
    return advapi


def read_password(host: str, username: str) -> str | None:
    """Read the saved password for this exact host and account, if present."""
    advapi = _api()
    credential = ctypes.POINTER(_Credential)()
    if not advapi.CredReadW(_target_name(host, username), _CRED_TYPE_GENERIC, 0,
                            ctypes.byref(credential)):
        error = ctypes.get_last_error()
        if error == _ERROR_NOT_FOUND:
            return None
        raise ctypes.WinError(error)
    try:
        value = credential.contents
        blob = ctypes.string_at(value.CredentialBlob, value.CredentialBlobSize)
        return blob.decode("utf-16-le")
    finally:
        advapi.CredFree(credential)


def write_password(host: str, username: str, password: str) -> None:
    """Save a password as a per-user generic credential."""
    advapi = _api()
    blob = password.encode("utf-16-le")
    blob_buffer = ctypes.create_string_buffer(blob)
    credential = _Credential(
        Type=_CRED_TYPE_GENERIC,
        TargetName=_target_name(host, username),
        CredentialBlobSize=len(blob),
        CredentialBlob=ctypes.cast(blob_buffer, ctypes.POINTER(ctypes.c_ubyte)),
        Persist=_CRED_PERSIST_LOCAL_MACHINE,
        UserName=username,
    )
    if not advapi.CredWriteW(ctypes.byref(credential), 0):
        raise ctypes.WinError(ctypes.get_last_error())


def delete_password(host: str, username: str) -> None:
    """Remove a saved password; an already absent credential is fine."""
    advapi = _api()
    if not advapi.CredDeleteW(_target_name(host, username), _CRED_TYPE_GENERIC, 0):
        error = ctypes.get_last_error()
        if error != _ERROR_NOT_FOUND:
            raise ctypes.WinError(error)


__all__ = ["read_password", "write_password", "delete_password"]
