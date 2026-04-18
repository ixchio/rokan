"""
Rokan Proactive Engine — Ambient awareness.
This is what separates FRIDAY from a chatbot. Rokan speaks first.

Watches: CPU, RAM, disk, battery, network, processes, services, idle time,
USB plug/unplug, active window changes. Fires alerts with actionable context.
"""

from __future__ import annotations

import os
import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Optional

from rokan_core.config import get_config


@dataclass
class Alert:
    """A proactive alert from the system."""
    type: str
    severity: str  # info, warning, critical
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)
    dismissed: bool = False


class ProactiveEngine:
    """
    Background watcher. Monitors the full system and fires alerts.
    FRIDAY doesn't wait for you to ask. It speaks first.
    """

    def __init__(self, on_alert: Optional[Callable[[Alert], None]] = None):
        cfg = get_config().proactive
        self._enabled = cfg.enabled
        self._interval = cfg.check_interval
        self._on_alert = on_alert

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._alerts: list[Alert] = []
        self._seen: set[str] = set()

        sys_cfg = get_config().system
        self._cpu_thresh = sys_cfg.cpu_threshold
        self._mem_thresh = sys_cfg.memory_threshold
        self._disk_thresh = sys_cfg.disk_threshold

        # State tracking for change detection
        self._last_window: str = ""
        self._window_start: float = 0
        self._last_usb_count: int = -1
        self._last_battery_plugged: Optional[bool] = None
        self._last_failed_services: set[str] = set()
        self._idle_alerted: bool = False

    def start(self):
        if not self._enabled or self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)

    @property
    def pending_alerts(self) -> list[Alert]:
        return [a for a in self._alerts if not a.dismissed]

    def dismiss_all(self):
        for a in self._alerts:
            a.dismissed = True

    def _fire(self, alert: Alert):
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

        def _reset():
            time.sleep(300)
            self._seen.discard(key)
        threading.Thread(target=_reset, daemon=True).start()

    def _loop(self):
        try:
            import psutil
        except ImportError:
            return

        while self._running:
            try:
                self._check_resources(psutil)
                self._check_battery(psutil)
                self._check_window_focus()
                self._check_idle()
                self._check_usb()
                self._check_services()
                self._check_network_drop(psutil)
            except Exception:
                pass
            time.sleep(self._interval)

    # ── Resource checks ──────────────────────────────────────────

    def _check_resources(self, psutil):
        cfg = get_config().proactive

        if cfg.alert_on_high_cpu:
            cpu = psutil.cpu_percent(interval=1)
            if cpu > self._cpu_thresh:
                culprit = self._find_top_process(psutil, "cpu_percent")
                severity = "critical" if cpu > 95 else "warning"
                msg = f"CPU at {cpu:.0f}%"
                if culprit:
                    msg += f" — {culprit['name']} is using {culprit['cpu_percent']:.0f}%"
                self._fire(Alert(type="high_cpu", severity=severity, message=msg,
                                 metadata={"cpu": cpu, "culprit": culprit}))

        if cfg.alert_on_high_memory:
            mem = psutil.virtual_memory()
            if mem.percent > self._mem_thresh:
                culprit = self._find_top_process(psutil, "memory_percent")
                severity = "critical" if mem.percent > 95 else "warning"
                avail = mem.available / 1024**3
                msg = f"RAM at {mem.percent:.0f}% — {avail:.1f}GB free"
                if culprit:
                    mb = (culprit.get("memory_info") and culprit["memory_info"].rss or 0) / 1024**2
                    msg += f". {culprit['name']} using {mb:.0f}MB"
                self._fire(Alert(type="high_memory", severity=severity, message=msg))

        if cfg.alert_on_disk_full:
            disk = psutil.disk_usage("/")
            if disk.percent > self._disk_thresh:
                free = disk.free / 1024**3
                severity = "critical" if disk.percent > 95 else "warning"
                self._fire(Alert(type="disk_full", severity=severity,
                                 message=f"Disk at {disk.percent:.0f}% — {free:.1f}GB free"))

        if cfg.alert_on_long_process:
            threshold_sec = cfg.long_process_minutes * 60
            now = time.time()
            for p in psutil.process_iter(["pid", "name", "create_time", "cpu_percent"]):
                try:
                    info = p.info
                    runtime = now - (info.get("create_time") or now)
                    if runtime > threshold_sec and (info.get("cpu_percent") or 0) > 50:
                        mins = int(runtime / 60)
                        self._fire(Alert(
                            type="long_process", severity="info",
                            message=f"'{info['name']}' running {mins}min at {info['cpu_percent']:.0f}% CPU",
                            metadata={"pid": info["pid"]},
                        ))
                except Exception:
                    pass

    # ── Battery awareness ────────────────────────────────────────

    def _check_battery(self, psutil):
        try:
            bat = psutil.sensors_battery()
        except Exception:
            return
        if not bat:
            return

        # Low battery
        if not bat.power_plugged and bat.percent <= 20:
            severity = "critical" if bat.percent <= 10 else "warning"
            mins = round(bat.secsleft / 60) if bat.secsleft > 0 else 0
            msg = f"Battery at {bat.percent:.0f}%"
            if mins:
                msg += f" — {mins} minutes left"
            self._fire(Alert(type="low_battery", severity=severity, message=msg))

        # Charger plugged/unplugged
        if self._last_battery_plugged is not None and bat.power_plugged != self._last_battery_plugged:
            if bat.power_plugged:
                self._fire(Alert(type="charger", severity="info",
                                 message=f"Charger connected. Battery at {bat.percent:.0f}%"))
            else:
                self._fire(Alert(type="charger", severity="info",
                                 message=f"Charger disconnected. Battery at {bat.percent:.0f}%"))
        self._last_battery_plugged = bat.power_plugged

    # ── Window focus tracking ────────────────────────────────────

    def _check_window_focus(self):
        """Track what app the user is focused on. Alert if stuck too long."""
        try:
            result = subprocess.run(
                ["xdotool", "getactivewindow", "getwindowname"],
                capture_output=True, text=True, timeout=2,
            )
            window = result.stdout.strip() if result.returncode == 0 else ""
        except Exception:
            return

        if not window:
            return

        now = time.time()
        if window != self._last_window:
            # Window changed — check if we were on previous one too long
            if self._last_window and self._window_start:
                duration = now - self._window_start
                if duration > 2400:  # 40+ minutes on same window
                    mins = int(duration / 60)
                    self._fire(Alert(
                        type="focus_stuck", severity="info",
                        message=f"You've been on '{self._last_window[:50]}' for {mins} minutes",
                    ))
            self._last_window = window
            self._window_start = now

    # ── Idle detection ───────────────────────────────────────────

    def _check_idle(self):
        """Detect if user has been idle (no mouse/keyboard) for too long."""
        try:
            result = subprocess.run(
                ["xprintidle"], capture_output=True, text=True, timeout=2,
            )
            idle_ms = int(result.stdout.strip())
            idle_min = idle_ms / 60000
        except Exception:
            return

        if idle_min > 30 and not self._idle_alerted:
            self._idle_alerted = True
            self._fire(Alert(
                type="idle", severity="info",
                message=f"You've been away for {int(idle_min)} minutes. System's fine.",
            ))
        elif idle_min < 5:
            self._idle_alerted = False

    # ── USB device changes ───────────────────────────────────────

    def _check_usb(self):
        """Detect USB device plug/unplug events."""
        try:
            result = subprocess.run(
                ["lsusb"], capture_output=True, text=True, timeout=2,
            )
            count = len([l for l in result.stdout.splitlines() if l.strip()])
        except Exception:
            return

        if self._last_usb_count >= 0 and count != self._last_usb_count:
            if count > self._last_usb_count:
                self._fire(Alert(type="usb", severity="info",
                                 message=f"USB device connected ({count} devices now)"))
            else:
                self._fire(Alert(type="usb", severity="info",
                                 message=f"USB device disconnected ({count} devices now)"))
        self._last_usb_count = count

    # ── Failed services ──────────────────────────────────────────

    def _check_services(self):
        """Detect newly failed systemd services."""
        try:
            result = subprocess.run(
                "systemctl --user list-units --state=failed --no-legend --no-pager 2>/dev/null; "
                "systemctl list-units --state=failed --no-legend --no-pager 2>/dev/null",
                shell=True, capture_output=True, text=True, timeout=5,
            )
            current = set()
            for line in result.stdout.splitlines():
                parts = line.split()
                if parts:
                    current.add(parts[0])
        except Exception:
            return

        new_failures = current - self._last_failed_services
        for svc in new_failures:
            self._fire(Alert(type="service_failed", severity="warning",
                             message=f"Service '{svc}' just failed"))
        self._last_failed_services = current

    # ── Network drop ─────────────────────────────────────────────

    def _check_network_drop(self, psutil):
        """Detect if internet connectivity dropped."""
        try:
            addrs = psutil.net_if_addrs()
            stats = psutil.net_if_stats()
            has_active = False
            for iface, st in stats.items():
                if st.isup and iface != "lo" and iface in addrs:
                    has_active = True
                    break
            if not has_active:
                self._fire(Alert(type="network_down", severity="warning",
                                 message="All network interfaces are down"))
        except Exception:
            pass

    # ── Helpers ───────────────────────────────────────────────────

    @staticmethod
    def _find_top_process(psutil, sort_key: str) -> Optional[dict]:
        """Find the process using the most of a resource."""
        best = None
        best_val = 0
        for p in psutil.process_iter(["name", "pid", "cpu_percent", "memory_percent", "memory_info"]):
            try:
                val = p.info.get(sort_key, 0) or 0
                if val > best_val:
                    best_val = val
                    best = p.info
            except Exception:
                pass
        return best
