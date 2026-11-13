"""Terminal interrupts must leave neither the Qt loop nor its worker running."""
import os
import signal
import subprocess
import sys
import time

import pytest

pytest.importorskip("PySide6")


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX terminal signals")
@pytest.mark.parametrize("action", ["interrupt", "close"])
def test_native_shutdown_stops_worker_and_exits_without_a_core_dump(tmp_path, action):
    script = r'''
import signal
import subprocess
import sys
from pathlib import Path
import resource
from PySide6.QtCore import QTimer
from isharescreen.gui import native_connect, native_entry, native_session
from isharescreen.tui.storage import ConnectFormValues

directory = Path(sys.argv[1])
action = sys.argv[2]
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
native_connect.load_last = lambda: None
child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
(directory / 'child-pid').write_text(str(child.pid))

class Session(native_session.NativeSession):
    def start(self, values):
        self._proc = child
        self.status.emit({'status': 'running'})
        self.snapshot.emit({'loss_total': 0})
    def stop(self):
        if child.poll() is None:
            child.terminate()
        child.wait(timeout=3)
        (directory / 'stopped').write_text('yes')

native_session.NativeSession = Session
class Controller(native_entry._NativeController):
    def __init__(self, window, session):
        super().__init__(window, session)
        QTimer.singleShot(0, self.begin)
    def begin(self):
        self._connect(ConnectFormValues(
            host='test.invalid', user='test', password='', advertise='auto',
            audio=False, curtain=False, hdr=False, share_console=False, alt_session=False))
        (directory / 'ready').write_text('yes')
        if action == 'close':
            QTimer.singleShot(20, self.close_dashboard)
    def close_dashboard(self):
        self.dashboard.close()
        QTimer.singleShot(20, self.connect_window.close)
native_entry._NativeController = Controller
original_handler = signal.getsignal(signal.SIGINT)
result = native_entry.main(['iss'])
assert signal.getsignal(signal.SIGINT) == original_handler
raise SystemExit(result)
'''
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen",
               XDG_STATE_HOME=str(tmp_path / "state"),
               XDG_CACHE_HOME=str(tmp_path / "cache"))
    proc = subprocess.Popen([sys.executable, "-c", script, str(tmp_path), action],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, env=env)
    child_pid = None
    try:
        deadline = time.monotonic() + 10
        while not (tmp_path / "ready").exists():
            assert proc.poll() is None, proc.communicate(timeout=1)
            assert time.monotonic() < deadline, "native GUI failed to start"
            time.sleep(0.01)
        child_pid = int((tmp_path / "child-pid").read_text())
        if action == "interrupt":
            proc.send_signal(signal.SIGINT)
        stdout, stderr = proc.communicate(timeout=5)
        assert proc.returncode == (130 if action == "interrupt" else 0), (stdout, stderr)
        assert (tmp_path / "stopped").read_text() == "yes"
        assert "KeyboardInterrupt" not in stderr
        with pytest.raises(ProcessLookupError):
            os.kill(child_pid, 0)
        child_pid = None
    finally:
        if proc.poll() is None:
            proc.kill()
        if child_pid is None and (tmp_path / "child-pid").exists():
            child_pid = int((tmp_path / "child-pid").read_text())
        if child_pid is not None:
            try:
                os.kill(child_pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        proc.communicate(timeout=3)
