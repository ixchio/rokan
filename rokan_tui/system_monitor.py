"""
System monitor — background thread polling CPU / RAM / Disk.
Pushes updates via callback to the TUI sidebar.
"""

import threading
import time

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False


class SystemMonitor:
    """Lightweight system resource poller."""

    def __init__(self, interval: float = 3.0):
        self._interval = interval
        self._running = False
        self._thread: threading.Thread | None = None
        self.stats: dict = {
            "cpu": 0.0,
            "cpu_cores": "",
            "ram": 0.0,
            "ram_used": "–",
            "disk": 0.0,
            "disk_used": "–",
        }

    def start(self, callback_func=None) -> None:
        if not _HAS_PSUTIL:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, args=(callback_func,), daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def _loop(self, callback) -> None:
        while self._running:
            try:
                cpu = psutil.cpu_percent(interval=1)
                mem = psutil.virtual_memory()
                disk = psutil.disk_usage("/")

                self.stats.update(
                    {
                        "cpu": cpu,
                        "cpu_cores": f"{psutil.cpu_count()}C",
                        "ram": mem.percent,
                        "ram_used": f"{mem.used // (1024**3)}G/{mem.total // (1024**3)}G",
                        "disk": disk.percent,
                        "disk_used": f"{disk.used // (1024**3)}G/{disk.total // (1024**3)}G",
                    }
                )

                if callback:
                    callback(self.stats)

            except Exception:
                pass

            time.sleep(max(self._interval - 1, 1))
