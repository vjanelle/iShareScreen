"""Worker-process and loopback control client for the native Windows UI."""
from __future__ import annotations

import http.server
import json
import logging
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

from PySide6.QtCore import QObject, Signal

from ..tui.storage import ConnectFormValues, save_last

log = logging.getLogger("iss.native")


def _update_saved_password(values: ConnectFormValues) -> None:
    """Best-effort credential persistence; never block a connection attempt."""
    try:
        from .windows_credentials import delete_password, write_password
        if values.save_password:
            write_password(values.host, values.user, values.password)
        else:
            delete_password(values.host, values.user)
    except OSError as exc:
        log.warning("could not update saved credential: %s", exc)


def _worker_arguments(values: ConnectFormValues, socket_path: str, log_path: str) -> list[str]:
    """Translate saved UI preferences to the CLI's supported arguments."""
    args = [
        "--host", values.host.strip(), "-u", values.user.strip(),
        "--password-stdin", "--frontend", "desktop",
        "--control-socket", socket_path, "--log-file", log_path,
    ]
    resolution = (values.advertise or "auto").strip().lower()
    if resolution and resolution != "auto":
        scale = (values.hidpi or "1.0").strip()
        args += ["--advertise", f"{resolution}@{scale}"]
    else:
        args += ["--hidpi", (values.hidpi or "auto").strip()]
    if values.decoder and values.decoder != "auto":
        args += ["--decoder", values.decoder]
    if not values.audio:
        args.append("--no-audio")
    if not values.curtain:
        args.append("--no-curtain")
    if values.hdr:
        args.append("--hdr")
    if values.share_console:
        args.append("--share-console")
    if values.alt_session:
        args.append("--alt-session")
    return args


def _worker_command(executable: str, arguments: list[str], *, frozen: bool) -> list[str]:
    if frozen:
        return [executable, "--iss-worker", *arguments]
    return [executable, "-m", "isharescreen.tui.entry", "--iss-worker", *arguments]


def _take_json_lines(buffer: bytes) -> tuple[list[dict[str, Any]], bytes]:
    """Parse complete newline-delimited JSON objects and retain a partial line."""
    messages: list[dict[str, Any]] = []
    lines = buffer.split(b"\n")
    remainder = lines.pop()
    for raw in lines:
        if not raw.strip():
            continue
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if isinstance(value, dict):
            messages.append(value)
    return messages, remainder


class _ChoiceServer(http.server.ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class NativeSession(QObject):
    """Launch and supervise one session worker without blocking Qt's UI thread."""

    status = Signal(dict)
    hello = Signal(dict)
    snapshot = Signal(dict)
    event = Signal(dict)
    log_line = Signal(str)
    finished = Signal(int)
    choice_requested = Signal(str, object, object)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._proc: subprocess.Popen[str] | None = None
        self._ctrl: socket.socket | None = None
        self._ctrl_lock = threading.Lock()
        self._stop_evt = threading.Event()
        self._temp_dir: str | None = None
        self._choice_server: _ChoiceServer | None = None
        self._choice_thread: threading.Thread | None = None
        self._generation = 0
        self._host = ""

    @property
    def running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def start(self, values: ConnectFormValues) -> None:
        self._generation += 1
        generation = self._generation
        self.stop()
        self._stop_evt = threading.Event()
        self._host = values.host
        self._temp_dir = tempfile.mkdtemp(prefix="iss-session-")
        socket_path = str(Path(self._temp_dir) / "control")
        log_path = str(Path(self._temp_dir) / "session.log")
        values.frontend = "desktop"
        save_last(values)
        _update_saved_password(values)
        self.status.emit({"status": "connecting", "host": values.host, "frontend": "desktop"})

        self._start_choice_server()
        env = dict(os.environ)
        if self._choice_server is not None:
            port = self._choice_server.server_address[1]
            env["ISS_SESSION_CHOICE_URL"] = f"http://127.0.0.1:{port}/session-choice"
        command = _worker_command(
            sys.executable,
            _worker_arguments(values, socket_path, log_path),
            frozen=bool(getattr(sys, "frozen", False)),
        )
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
        try:
            self._proc = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                env=env,
                creationflags=creationflags,
            )
            assert self._proc.stdin is not None
            self._proc.stdin.write(values.password + "\n")
            self._proc.stdin.flush()
            self._proc.stdin.close()
        except OSError as exc:
            self.log_line.emit(f"Could not start session worker: {exc}")
            self._finish_choice_server()
            self._cleanup_temp_dir()
            self._proc = None
            self.status.emit({"status": "error", "host": values.host, "message": str(exc)})
            self.finished.emit(1)
            return

        threading.Thread(target=self._pump_output, args=(generation,), daemon=True,
                         name="iss-native-log").start()
        threading.Thread(target=self._read_control, args=(socket_path, generation), daemon=True,
                         name="iss-native-control").start()
        threading.Thread(target=self._wait_worker, args=(generation,), daemon=True,
                         name="iss-native-worker").start()

    def send_action(self, action: dict[str, Any]) -> None:
        line = (json.dumps(action, separators=(",", ":")) + "\n").encode("utf-8")
        with self._ctrl_lock:
            conn = self._ctrl
            if conn is None:
                self.log_line.emit("Session control channel is not connected yet.")
                return
            try:
                conn.sendall(line)
            except OSError as exc:
                self.log_line.emit(f"Session control command failed: {exc}")

    def stop(self) -> None:
        self._stop_evt.set()
        proc = self._proc
        if proc is None:
            self._finish_choice_server()
            self._cleanup_temp_dir()
            return
        self.send_action({"action": "quit"})
        self._stop_evt.set()
        if proc.poll() is None:
            try:
                proc.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                proc.terminate()
                try:
                    proc.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=2.0)
        self._close_control_socket()
        self._finish_choice_server()
        self._cleanup_temp_dir()
        if self._proc is proc:
            self._proc = None

    def answer_session_choice(self, response_event: threading.Event,
                              response: dict[str, str], choice: str) -> None:
        response["choice"] = "alt_session" if choice == "alt_session" else "share_console"
        response_event.set()

    def _start_choice_server(self) -> None:
        owner = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802
                if self.path != "/session-choice" or self.client_address[0] != "127.0.0.1":
                    self.send_error(404)
                    return
                try:
                    body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
                    fields = parse_qs(body.decode("utf-8", errors="replace"))
                    console_user = (fields.get("console_user") or [""])[0]
                    completed = threading.Event()
                    response: dict[str, str] = {"choice": "share_console"}
                    owner.choice_requested.emit(console_user, completed, response)
                    completed.wait(timeout=50.0)
                    payload = response["choice"].encode("ascii")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain; charset=utf-8")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                except (OSError, ValueError):
                    self.send_error(400)

            def log_message(self, *_args) -> None:
                return

        try:
            self._choice_server = _ChoiceServer(("127.0.0.1", 0), Handler)
            self._choice_thread = threading.Thread(
                target=self._choice_server.serve_forever, daemon=True,
                name="iss-native-choice",
            )
            self._choice_thread.start()
        except OSError as exc:
            self.log_line.emit(f"Session-choice prompt unavailable: {exc}")
            self._choice_server = None

    def _pump_output(self, generation: int) -> None:
        proc = self._proc
        if proc is None or proc.stdout is None:
            return
        try:
            for line in proc.stdout:
                if generation != self._generation:
                    return
                self.log_line.emit(line.rstrip("\r\n"))
        except (OSError, ValueError):
            return

    def _read_control(self, socket_path: str, generation: int) -> None:
        port_file = Path(socket_path + ".port")
        conn: socket.socket | None = None
        deadline = time.monotonic() + 30.0
        port: int | None = None
        while not self._stop_evt.is_set() and generation == self._generation:
            proc = self._proc
            if proc is None or proc.poll() is not None:
                break
            try:
                if port_file.exists():
                    port = int(port_file.read_text(encoding="ascii").strip())
                    break
            except (OSError, ValueError):
                pass
            if time.monotonic() >= deadline:
                self.log_line.emit("Timed out waiting for the session control endpoint.")
                return
            time.sleep(0.2)
        if port is None or self._stop_evt.is_set() or generation != self._generation:
            return

        deadline = time.monotonic() + 15.0
        while not self._stop_evt.is_set() and generation == self._generation:
            try:
                conn = socket.create_connection(("127.0.0.1", port), timeout=1.0)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    self.log_line.emit("Could not connect to the session control endpoint.")
                    return
                time.sleep(0.2)
        if conn is None:
            return
        conn.settimeout(0.5)
        with self._ctrl_lock:
            self._ctrl = conn
        self.status.emit({"status": "running", "host": self._host, "frontend": "desktop"})
        buffer = b""
        try:
            while not self._stop_evt.is_set() and generation == self._generation:
                try:
                    chunk = conn.recv(16384)
                except socket.timeout:
                    continue
                if not chunk:
                    break
                messages, buffer = _take_json_lines(buffer + chunk)
                for message in messages:
                    kind = message.get("type")
                    if kind == "hello":
                        self.hello.emit(message.get("session", {}))
                    elif kind == "snapshot":
                        self.snapshot.emit(message.get("data", {}))
                    elif kind == "event":
                        self.event.emit(message)
        except OSError as exc:
            if not self._stop_evt.is_set():
                self.log_line.emit(f"Session control channel closed: {exc}")
        finally:
            with self._ctrl_lock:
                if self._ctrl is conn:
                    self._ctrl = None
            try:
                conn.close()
            except OSError:
                pass

    def _wait_worker(self, generation: int) -> None:
        proc = self._proc
        if proc is None:
            return
        code = proc.wait()
        if generation != self._generation:
            return
        self._stop_evt.set()
        self._close_control_socket()
        self._finish_choice_server()
        self._cleanup_temp_dir()
        self.status.emit({"status": "ended", "exit_code": code})
        self.finished.emit(code)
        if self._proc is proc:
            self._proc = None

    def _close_control_socket(self) -> None:
        with self._ctrl_lock:
            conn, self._ctrl = self._ctrl, None
        if conn is not None:
            try:
                conn.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                conn.close()
            except OSError:
                pass

    def _finish_choice_server(self) -> None:
        server, self._choice_server = self._choice_server, None
        if server is None:
            return
        try:
            server.shutdown()
        except (OSError, RuntimeError):
            pass
        server.server_close()

    def _cleanup_temp_dir(self) -> None:
        directory, self._temp_dir = self._temp_dir, None
        if directory:
            import shutil
            shutil.rmtree(directory, ignore_errors=True)


__all__ = ["NativeSession"]
