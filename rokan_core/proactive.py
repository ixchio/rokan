"""
Rokan Proactive Engine — Ambient awareness.
This is what makes it feel like F.R.I.D.A.Y. instead of a chatbot.
Runs in the background, watches the system, alerts before you ask.
"""

from __future__ import annotations

import platform
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Optional

from rokan_core.config import get_config


@dataclass
class Alert:
    """A proactive alert from the system."""
    type: str  # high_cpu, high_memory, disk_full, long_process
    severity: str  # info, warning, critical
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)
    dismissed: bool = False


class ProactiveEngine:
    """
    Background watcher. Monitors system state and fires alerts.
    The TUI subscribes to these alerts and displays them naturally.
    """

    def __init__(self, on_alert: Optional[Callable[[Alert], None]] = None):
        cfg = get_config().proactive
        self._enabled = cfg.enabled
        self._interval = cfg.check_interval
        self._on_alert = on_alert

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._alerts: list[Alert] = []
        self._seen: set[str] = set()  # dedup key → already alerted

        # Thresholds from config
        sys_cfg = get_config().system
        self._cpu_thresh = sys_cfg.cpu_threshold
        self._mem_thresh = sys_cfg.memory_threshold
        self._disk_thresh = sys_cfg.disk_threshold

    def start(self):
        """Start background monitoring."""
        if not self._enabled or self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop monitoring."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)

    @property
    def pending_alerts(self) -> list[Alert]:
        """Get undismissed alerts."""
        return [a for a in self._alerts if not a.dismissed]

    def dismiss_all(self):
        """Dismiss all current alerts."""
        for a in self._alerts:
            a.dismissed = True

    def _fire(self, alert: Alert):
        """Fire an alert (dedup by type + severity)."""
        key = f"{alert.type}:{alert.severity}"
        if key in self._seen:
            return
        self._seen.add(key)

        self._alerts.append(alert)
        if self._on_alert:
            try:
                self._on_alert(alert)
            except Exception:
                pass

        # Reset dedup after 5 minutes (so it can fire again)
        def _reset():
            time.sleep(300)
            self._seen.discard(key)
        threading.Thread(target=_reset, daemon=True).start()

    def _loop(self):
        """Main monitoring loop."""
        try:
            import psutil
        except ImportError:
            return

        while self._running:
            try:
                self._check_system(psutil)
            except Exception:
                pass
            time.sleep(self._interval)

    def _check_system(self, psutil):
        """Run all system checks."""
        cfg = get_config().proactive

        # CPU check
        if cfg.alert_on_high_cpu:
            cpu = psutil.cpu_percent(interval=1)
            if cpu > self._cpu_thresh:
                # Find the culprit
                top_proc = ""
                for p in psutil.process_iter(["name", "cpu_percent"]):
                    try:
                        if p.info["cpu_percent"] and p.info["cpu_percent"] > 20:
                            top_proc = f" (top: {p.info['name']} at {p.info['cpu_percent']:.0f}%)"
                            break
                    except Exception:
                        pass

                severity = "critical" if cpu > 95 else "warning"
                self._fire(Alert(
                    type="high_cpu",
                    severity=severity,
                    message=f"CPU at {cpu:.0f}%{top_proc}",
                    metadata={"cpu_percent": cpu},
                ))

        # Memory check
        if cfg.alert_on_high_memory:
            mem = psutil.virtual_memory()
            if mem.percent > self._mem_thresh:
                avail_gb = mem.available / (1024 ** 3)
                severity = "critical" if mem.percent > 95 else "warning"
                self._fire(Alert(
                    type="high_memory",
                    severity=severity,
                    message=f"RAM at {mem.percent:.0f}% — {avail_gb:.1f}GB free",
                    metadata={"memory_percent": mem.percent},
                ))

        # Disk check
        if cfg.alert_on_disk_full:
            disk = psutil.disk_usage("/")
            if disk.percent > self._disk_thresh:
                free_gb = disk.free / (1024 ** 3)
                severity = "critical" if disk.percent > 95 else "warning"
                self._fire(Alert(
                    type="disk_full",
                    severity=severity,
                    message=f"Disk at {disk.percent:.0f}% — {free_gb:.1f}GB free",
                    metadata={"disk_percent": disk.percent},
                ))

        # Long process check
        if cfg.alert_on_long_process:
            threshold_sec = cfg.long_process_minutes * 60
            now = time.time()
            for p in psutil.process_iter(["pid", "name", "create_time", "cpu_percent"]):
                try:
                    info = p.info
                    runtime = now - info["create_time"]
                    if (
                        runtime > threshold_sec
                        and info.get("cpu_percent", 0)
                        and info["cpu_percent"] > 50
                    ):
                        mins = int(runtime / 60)
                        self._fire(Alert(
                            type="long_process",
                            severity="info",
                            message=(
                                f"'{info['name']}' (PID {info['pid']}) running {mins}min "
                                f"at {info['cpu_percent']:.0f}% CPU"
                            ),
                            metadata={"pid": info["pid"], "runtime_min": mins},
                        ))
                except (psutil.NoSuchProcess, psutil.AccessDenied, KeyError):
                    pass
