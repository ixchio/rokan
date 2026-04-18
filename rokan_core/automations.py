"""
Rokan Automations — Natural language cron + event-driven triggers.

"Every morning at 9, check my email"
"When disk goes above 90%, find largest files"
"Every Friday at 5pm, remind me to submit timesheet"
"After 30 minutes of idle, lock the screen"

Stores rules in SQLite. Background thread checks conditions every 30s.
"""

from __future__ import annotations

import json
import re
import sqlite3
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Optional

from rokan_core.config import get_config


@dataclass
class Automation:
    """A stored automation rule."""
    id: int
    name: str
    trigger_type: str  # time, interval, system, idle
    trigger_config: dict  # parsed trigger details
    action: str  # the command/query to execute
    enabled: bool = True
    last_fired: str = ""
    created_at: str = ""


class AutomationEngine:
    """
    Background automation runner. Stores rules in SQLite,
    checks conditions every tick, fires actions via callback.
    """

    def __init__(
        self,
        on_fire: Optional[Callable[[Automation], None]] = None,
        db_path: Optional[str] = None,
    ):
        self._on_fire = on_fire
        data_dir = Path.home() / ".rokan"
        data_dir.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path or str(data_dir / "automations.db")
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS automations (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    name            TEXT NOT NULL,
                    trigger_type    TEXT NOT NULL,
                    trigger_config  TEXT NOT NULL DEFAULT '{}',
                    action          TEXT NOT NULL,
                    enabled         INTEGER DEFAULT 1,
                    last_fired      TEXT DEFAULT '',
                    created_at      TEXT NOT NULL
                )
            """)

    # ── CRUD ─────────────────────────────────────────────────────

    def add(self, name: str, trigger_type: str, trigger_config: dict, action: str) -> int:
        """Add an automation rule. Returns the ID."""
        now = datetime.now().isoformat()
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO automations (name, trigger_type, trigger_config, action, created_at) "
                "VALUES (?,?,?,?,?)",
                (name, trigger_type, json.dumps(trigger_config), action, now),
            )
            return cur.lastrowid

    def remove(self, auto_id: int) -> bool:
        with self._conn() as conn:
            conn.execute("DELETE FROM automations WHERE id = ?", (auto_id,))
            return conn.total_changes > 0

    def list_all(self) -> list[Automation]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM automations ORDER BY id").fetchall()
        return [self._row_to_auto(r) for r in rows]

    def toggle(self, auto_id: int, enabled: bool) -> bool:
        with self._conn() as conn:
            conn.execute(
                "UPDATE automations SET enabled = ? WHERE id = ?",
                (1 if enabled else 0, auto_id),
            )
            return conn.total_changes > 0

    # ── Natural Language Parser ──────────────────────────────────

    def parse_and_add(self, text: str) -> Optional[Automation]:
        """
        Parse natural language into an automation.

        Supported patterns:
        - "every day at 9am, check email"
        - "every monday at 10:00, run git pull"
        - "every 30 minutes, check system status"
        - "when idle for 10 minutes, lock screen"
        - "when cpu above 90, alert me"
        - "when disk above 90%, find largest files"
        """
        q = text.lower().strip()

        # Remove leading words
        for prefix in ["automate ", "schedule ", "create automation ", "add automation "]:
            if q.startswith(prefix):
                q = q[len(prefix):]
                break

        # Pattern: "every [day|weekday] at HH:MM, ACTION"
        m = re.match(
            r'every\s+(?:day\s+)?at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?,?\s+(.+)',
            q,
        )
        if m:
            hour = int(m.group(1))
            minute = int(m.group(2) or 0)
            ampm = m.group(3)
            action = m.group(4)

            if ampm == "pm" and hour < 12:
                hour += 12
            elif ampm == "am" and hour == 12:
                hour = 0

            config = {"hour": hour, "minute": minute}
            auto_id = self.add(f"daily at {hour:02d}:{minute:02d}", "daily", config, action)
            return self._get(auto_id)

        # Pattern: "every [weekday] at HH:MM, ACTION"
        days = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
                "friday": 4, "saturday": 5, "sunday": 6}
        m = re.match(
            r'every\s+(' + '|'.join(days.keys()) + r')\s+at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?,?\s+(.+)',
            q,
        )
        if m:
            day_name = m.group(1)
            hour = int(m.group(2))
            minute = int(m.group(3) or 0)
            ampm = m.group(4)
            action = m.group(5)

            if ampm == "pm" and hour < 12:
                hour += 12

            config = {"day": days[day_name], "hour": hour, "minute": minute}
            auto_id = self.add(f"weekly {day_name} {hour:02d}:{minute:02d}", "weekly", config, action)
            return self._get(auto_id)

        # Pattern: "every N minutes/hours, ACTION"
        m = re.match(r'every\s+(\d+)\s*(min|minute|hour|hr|sec|second)s?,?\s+(.+)', q)
        if m:
            val = int(m.group(1))
            unit = m.group(2)[0]  # m, h, s
            action = m.group(3)

            seconds = val * (3600 if unit == 'h' else 60 if unit == 'm' else 1)
            config = {"interval_seconds": seconds}
            auto_id = self.add(f"every {val}{unit}", "interval", config, action)
            return self._get(auto_id)

        # Pattern: "when idle for N minutes, ACTION"
        m = re.match(r'when\s+idle\s+(?:for\s+)?(\d+)\s*(min|minute|hour)s?,?\s+(.+)', q)
        if m:
            val = int(m.group(1))
            unit = m.group(2)[0]
            action = m.group(3)
            seconds = val * (3600 if unit == 'h' else 60)
            config = {"idle_seconds": seconds}
            auto_id = self.add(f"idle {val}{unit}", "idle", config, action)
            return self._get(auto_id)

        # Pattern: "when cpu/ram/disk above N%, ACTION"
        m = re.match(r'when\s+(cpu|ram|memory|disk)\s+(?:above|over|exceeds?)\s+(\d+)%?,?\s+(.+)', q)
        if m:
            metric = m.group(1)
            if metric == "memory":
                metric = "ram"
            threshold = int(m.group(2))
            action = m.group(3)
            config = {"metric": metric, "threshold": threshold}
            auto_id = self.add(f"{metric} > {threshold}%", "system", config, action)
            return self._get(auto_id)

        return None

    def _get(self, auto_id: int) -> Optional[Automation]:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM automations WHERE id = ?", (auto_id,)).fetchone()
        return self._row_to_auto(row) if row else None

    @staticmethod
    def _row_to_auto(row) -> Automation:
        return Automation(
            id=row["id"],
            name=row["name"],
            trigger_type=row["trigger_type"],
            trigger_config=json.loads(row["trigger_config"]),
            action=row["action"],
            enabled=bool(row["enabled"]),
            last_fired=row["last_fired"],
            created_at=row["created_at"],
        )

    # ── Background Runner ────────────────────────────────────────

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="rokan-automations")
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)

    def _loop(self):
        while self._running:
            try:
                self._tick()
            except Exception:
                pass
            time.sleep(30)

    def _tick(self):
        """Check all enabled automations and fire if conditions met."""
        now = datetime.now()
        automations = self.list_all()

        for auto in automations:
            if not auto.enabled:
                continue

            should_fire = False
            cfg = auto.trigger_config

            if auto.trigger_type == "daily":
                should_fire = self._check_daily(now, cfg, auto.last_fired)

            elif auto.trigger_type == "weekly":
                should_fire = self._check_weekly(now, cfg, auto.last_fired)

            elif auto.trigger_type == "interval":
                should_fire = self._check_interval(now, cfg, auto.last_fired)

            elif auto.trigger_type == "idle":
                should_fire = self._check_idle(cfg, auto.last_fired)

            elif auto.trigger_type == "system":
                should_fire = self._check_system(cfg, auto.last_fired)

            if should_fire:
                self._fire(auto)

    def _fire(self, auto: Automation):
        """Fire an automation and update last_fired."""
        now = datetime.now().isoformat()
        with self._conn() as conn:
            conn.execute(
                "UPDATE automations SET last_fired = ? WHERE id = ?",
                (now, auto.id),
            )

        if self._on_fire:
            try:
                self._on_fire(auto)
            except Exception:
                pass

    @staticmethod
    def _check_daily(now: datetime, cfg: dict, last_fired: str) -> bool:
        target_hour = cfg.get("hour", 9)
        target_min = cfg.get("minute", 0)

        if now.hour != target_hour or abs(now.minute - target_min) > 1:
            return False

        # Don't fire if already fired today
        if last_fired:
            try:
                last = datetime.fromisoformat(last_fired)
                if last.date() == now.date():
                    return False
            except Exception:
                pass
        return True

    @staticmethod
    def _check_weekly(now: datetime, cfg: dict, last_fired: str) -> bool:
        target_day = cfg.get("day", 0)
        target_hour = cfg.get("hour", 9)
        target_min = cfg.get("minute", 0)

        if now.weekday() != target_day:
            return False
        if now.hour != target_hour or abs(now.minute - target_min) > 1:
            return False

        if last_fired:
            try:
                last = datetime.fromisoformat(last_fired)
                if (now - last).total_seconds() < 3600:
                    return False
            except Exception:
                pass
        return True

    @staticmethod
    def _check_interval(now: datetime, cfg: dict, last_fired: str) -> bool:
        interval = cfg.get("interval_seconds", 3600)

        if not last_fired:
            return True

        try:
            last = datetime.fromisoformat(last_fired)
            elapsed = (now - last).total_seconds()
            return elapsed >= interval
        except Exception:
            return True

    @staticmethod
    def _check_idle(cfg: dict, last_fired: str) -> bool:
        threshold = cfg.get("idle_seconds", 600)

        try:
            import subprocess
            r = subprocess.run(
                "xprintidle 2>/dev/null",
                shell=True, capture_output=True, text=True, timeout=3,
            )
            if r.returncode == 0:
                idle_ms = int(r.stdout.strip())
                if idle_ms // 1000 < threshold:
                    return False
            else:
                return False
        except Exception:
            return False

        # Cooldown: don't fire again within the idle threshold
        if last_fired:
            try:
                last = datetime.fromisoformat(last_fired)
                if (datetime.now() - last).total_seconds() < threshold:
                    return False
            except Exception:
                pass
        return True

    @staticmethod
    def _check_system(cfg: dict, last_fired: str) -> bool:
        metric = cfg.get("metric", "cpu")
        threshold = cfg.get("threshold", 90)

        try:
            import psutil
            if metric == "cpu":
                val = psutil.cpu_percent(interval=0.5)
            elif metric == "ram":
                val = psutil.virtual_memory().percent
            elif metric == "disk":
                val = psutil.disk_usage("/").percent
            else:
                return False

            if val < threshold:
                return False
        except Exception:
            return False

        # Cooldown: 5 minutes between system alerts
        if last_fired:
            try:
                last = datetime.fromisoformat(last_fired)
                if (datetime.now() - last).total_seconds() < 300:
                    return False
            except Exception:
                pass
        return True
