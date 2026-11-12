"""Linux desktop credentials. Never use keyring's configurable fallback chain.

All operations are best effort; only explicit Secret Service and KWallet
backends are allowed. Exceptions deliberately omit backend text, which may
contain credential material. Secrets are never returned to the browser.
"""
from __future__ import annotations

import logging
import os
import sys
import threading

log = logging.getLogger(__name__)
_LOCK = threading.RLock()


def _candidates() -> list[type]:
    if not sys.platform.startswith("linux"):
        return []
    secret = []
    wallets = []
    try:
        from keyring.backends.SecretService import Keyring
        secret = [Keyring]
    except ImportError:
        pass
    try:
        from keyring.backends.kwallet import DBusKeyring

        class KWallet6(DBusKeyring):
            bus_name = "org.kde.kwalletd6"
            object_path = "/modules/kwalletd6"

        wallets = [KWallet6, DBusKeyring]
    except ImportError:
        pass
    kde = "KDE" in os.environ.get("XDG_CURRENT_DESKTOP", "").upper().split(":")
    return wallets + secret if kde else secret + wallets


def _backend():
    for candidate in _candidates():
        try:
            if candidate.priority > 0:
                backend = candidate()
                if hasattr(backend, "appid"):
                    backend.appid = "iShareScreen"
                return backend
        except Exception:
            continue
    return None


def _service(host: str) -> str:
    return "iShareScreen/" + host.strip()


def get_password(host: str, user: str) -> str | None:
    if not host.strip() or not user.strip():
        return None
    with _LOCK:
        try:
            backend = _backend()
            if backend is not None:
                return backend.get_password(_service(host), user.strip())
        except Exception:
            log.warning("Desktop keyring could not read the saved password; enter it manually.")
    return None


def set_password(host: str, user: str, password: str) -> bool:
    if not host.strip() or not user.strip() or not password:
        return False
    with _LOCK:
        try:
            backend = _backend()
            if backend is not None:
                backend.set_password(_service(host), user.strip(), password)
                # KWallet's Python backend does not check the D-Bus write status.
                if backend.get_password(_service(host), user.strip()) == password:
                    return True
        except Exception:
            pass
    log.warning("Desktop keyring could not save the password; no file fallback was used.")
    return False


def delete_password(host: str, user: str) -> bool:
    if not host.strip() or not user.strip():
        return False
    with _LOCK:
        try:
            backend = _backend()
            if backend is not None:
                service, username = _service(host), user.strip()
                if backend.get_password(service, username) is not None:
                    backend.delete_password(service, username)
                return backend.get_password(service, username) is None
        except Exception:
            pass
    log.warning("Desktop keyring could not forget the saved password.")
    return False
