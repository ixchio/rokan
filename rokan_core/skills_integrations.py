"""
Rokan Integration Skills — Git, Calendar, Email, Briefing, Automations.

These connect Rokan to real workflows. Not toy features.
"""

from __future__ import annotations

import datetime
import imaplib
import email
import json
import os
import re
import subprocess
from email.header import decode_header
from pathlib import Path
from typing import Optional

from rokan_core.skills import Skill, SkillResult


# ── Git Integration ────────────────────────────────────────────────

class GitSkill(Skill):
    """Full git integration — status, log, diff, commit, branch management."""
    name = "git"
    description = "Git operations — status, log, diff, commit, branch"
    triggers = [
        "git", "commit", "branch", "merge", "pull", "push",
        "diff", "log", "stash", "rebase", "cherry-pick",
        "git status", "git log", "uncommitted", "changes",
        "repo", "repository",
    ]
    priority = 75

    def can_handle(self, query: str) -> float:
        q = query.lower()
        if q.startswith("/git ") or q.startswith("git "):
            return 0.95
        if any(p in q for p in ["git status", "git log", "git diff", "uncommitted changes",
                                 "what branch", "commit message", "recent commits"]):
            return 0.9
        return super().can_handle(q)

    def execute(self, query: str, context: dict) -> SkillResult:
        q = query.lower().strip()
        for prefix in ("/git ", "git "):
            if q.startswith(prefix):
                q = q[len(prefix):]
                break

        # Find git repo
        repo_dir = self._find_repo()
        if not repo_dir:
            return SkillResult(
                content="no git repository found. cd into a repo or set one with /remember my repo is /path/to/repo",
                display_raw=True,
            )

        # Route to specific git operation
        if q in ("status", "st", "") or "status" in q or "changes" in q or "uncommitted" in q:
            return self._status(repo_dir)
        if q.startswith("log") or "recent commits" in q or "history" in q:
            return self._log(repo_dir, q)
        if q.startswith("diff") or "what changed" in q:
            return self._diff(repo_dir)
        if q.startswith("branch") or "what branch" in q or "current branch" in q:
            return self._branch(repo_dir)
        if q.startswith("stash"):
            return self._run_git(repo_dir, "stash " + q[5:].strip())
        if "commit message" in q or "generate commit" in q or "auto commit" in q:
            return self._generate_commit_msg(repo_dir)
        if q.startswith("add"):
            return self._run_git(repo_dir, "add " + q[3:].strip())

        # Passthrough: run any git command
        return self._run_git(repo_dir, q)

    def _find_repo(self) -> Optional[str]:
        """Find a git repo — check CWD, home, common locations."""
        candidates = [
            Path.cwd(),
            Path.home(),
        ]
        # Check common dev directories
        for d in ["projects", "code", "dev", "repos", "src", "workspace"]:
            p = Path.home() / d
            if p.exists():
                # Find first git repo in there
                for child in sorted(p.iterdir()):
                    if (child / ".git").exists():
                        candidates.insert(0, child)
                        break

        for p in candidates:
            if (p / ".git").exists():
                return str(p)

        return None

    def _status(self, repo: str) -> SkillResult:
        r = self._git(repo, "status --short --branch")
        branch_line = ""
        changes = []
        for line in r.splitlines():
            if line.startswith("##"):
                branch_line = line[3:]
            elif line.strip():
                changes.append(line)

        parts = [f"repo: {Path(repo).name}"]
        if branch_line:
            parts.append(f"branch: {branch_line}")
        if changes:
            parts.append(f"changes ({len(changes)}):")
            parts.extend(f"  {c}" for c in changes[:20])
        else:
            parts.append("clean — no uncommitted changes")

        return SkillResult(content="\n".join(parts), inject_as_context=True)

    def _log(self, repo: str, q: str) -> SkillResult:
        # Extract number of commits
        n = 10
        m = re.search(r'(\d+)', q)
        if m:
            n = min(int(m.group(1)), 50)

        r = self._git(repo, f"log --oneline --no-decorate -n {n}")
        return SkillResult(
            content=f"recent commits ({Path(repo).name}):\n{r}",
            inject_as_context=True,
        )

    def _diff(self, repo: str) -> SkillResult:
        r = self._git(repo, "diff --stat")
        if not r.strip():
            r = self._git(repo, "diff --cached --stat")
        if not r.strip():
            return SkillResult(content="no diff — working tree clean", display_raw=True)
        return SkillResult(
            content=f"diff summary:\n{r}",
            inject_as_context=True,
        )

    def _branch(self, repo: str) -> SkillResult:
        r = self._git(repo, "branch -a --no-color")
        return SkillResult(
            content=f"branches ({Path(repo).name}):\n{r}",
            inject_as_context=True,
        )

    def _generate_commit_msg(self, repo: str) -> SkillResult:
        """Generate a commit message from the current diff."""
        diff = self._git(repo, "diff --cached --stat")
        if not diff.strip():
            diff = self._git(repo, "diff --stat")
        if not diff.strip():
            return SkillResult(content="nothing to commit", display_raw=True)

        # Get detailed diff for context
        detailed = self._git(repo, "diff --cached")
        if not detailed:
            detailed = self._git(repo, "diff")

        # Truncate for context injection
        content = (
            f"[GIT DIFF for commit message generation]\n"
            f"repo: {Path(repo).name}\n"
            f"summary:\n{diff}\n\n"
            f"detailed diff (first 3000 chars):\n{detailed[:3000]}"
        )
        return SkillResult(content=content, inject_as_context=True)

    def _run_git(self, repo: str, cmd: str) -> SkillResult:
        r = self._git(repo, cmd)
        return SkillResult(content=f"$ git {cmd}\n{r}" if r else f"$ git {cmd}\n(done)", display_raw=True)

    @staticmethod
    def _git(repo: str, cmd: str) -> str:
        try:
            r = subprocess.run(
                f"git {cmd}",
                shell=True, capture_output=True, text=True,
                timeout=15, cwd=repo,
            )
            out = r.stdout.strip()
            err = r.stderr.strip()
            return out or err
        except Exception as e:
            return f"error: {e}"


# ── Calendar Integration ───────────────────────────────────────────

class CalendarSkill(Skill):
    """
    Calendar integration. Reads from:
    1. calcurse (terminal calendar — zero setup)
    2. Google Calendar (via gcalcli if installed)
    3. ical files in ~/.local/share/calendars/
    """
    name = "calendar"
    description = "Check calendar events and schedule"
    triggers = [
        "calendar", "schedule", "meeting", "event", "appointment",
        "what's today", "what's tomorrow", "agenda", "busy",
        "next meeting", "upcoming",
    ]
    priority = 70

    def can_handle(self, query: str) -> float:
        q = query.lower()
        if any(p in q for p in ["calendar", "schedule", "meeting", "agenda",
                                 "next meeting", "appointment", "what's today",
                                 "am i busy", "what do i have"]):
            return 0.85
        return super().can_handle(q)

    def execute(self, query: str, context: dict) -> SkillResult:
        q = query.lower().strip()

        results = []

        # Try gcalcli (Google Calendar)
        gcal = self._try_gcalcli(q)
        if gcal:
            results.append(gcal)

        # Try calcurse (terminal calendar)
        calcurse = self._try_calcurse(q)
        if calcurse:
            results.append(calcurse)

        if not results:
            return SkillResult(
                content="no calendar found. install gcalcli (google) or calcurse (local):\n"
                        "  sudo apt install calcurse\n"
                        "  pip install gcalcli",
                display_raw=True,
            )

        return SkillResult(
            content="\n\n".join(results),
            inject_as_context=True,
        )

    @staticmethod
    def _try_gcalcli(q: str) -> str:
        import shutil
        if not shutil.which("gcalcli"):
            return ""
        try:
            if "tomorrow" in q:
                cmd = "gcalcli agenda tomorrow 'tomorrow 23:59' --nocolor"
            elif "week" in q:
                cmd = "gcalcli agenda --nocolor"
            else:
                cmd = "gcalcli agenda today 'today 23:59' --nocolor"

            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            if r.stdout.strip():
                return f"[GOOGLE CALENDAR]\n{r.stdout.strip()}"
        except Exception:
            pass
        return ""

    @staticmethod
    def _try_calcurse(q: str) -> str:
        import shutil
        if not shutil.which("calcurse"):
            return ""
        try:
            if "tomorrow" in q:
                r = subprocess.run(
                    "calcurse -d 1 --output-datefmt='%H:%M'",
                    shell=True, capture_output=True, text=True, timeout=5,
                )
            else:
                r = subprocess.run(
                    "calcurse -d 0 --output-datefmt='%H:%M'",
                    shell=True, capture_output=True, text=True, timeout=5,
                )
            if r.stdout.strip():
                return f"[CALCURSE]\n{r.stdout.strip()}"
        except Exception:
            pass
        return ""


# ── Email Integration ──────────────────────────────────────────────

class EmailSkill(Skill):
    """
    Email integration via IMAP. Reads inbox, summarizes unread.
    Config in ~/.rokan/.env:
      IMAP_SERVER=imap.gmail.com
      IMAP_USER=you@gmail.com
      IMAP_PASSWORD=your-app-password
    """
    name = "email"
    description = "Check and summarize email inbox"
    triggers = [
        "email", "mail", "inbox", "unread", "messages",
        "check email", "check mail", "new emails",
    ]
    priority = 65

    def can_handle(self, query: str) -> float:
        q = query.lower()
        if any(p in q for p in ["check email", "check mail", "my inbox", "unread email",
                                 "new emails", "new mail"]):
            return 0.9
        if "email" in q or "mail" in q or "inbox" in q:
            return 0.75
        return super().can_handle(q)

    def execute(self, query: str, context: dict) -> SkillResult:
        # Load IMAP config from env
        from rokan_core.config import _load_env_file
        _load_env_file()

        server = os.environ.get("IMAP_SERVER", "")
        user = os.environ.get("IMAP_USER", "")
        password = os.environ.get("IMAP_PASSWORD", "")

        if not all([server, user, password]):
            return SkillResult(
                content="email not configured. add to ~/.rokan/.env:\n"
                        "  IMAP_SERVER=imap.gmail.com\n"
                        "  IMAP_USER=you@gmail.com\n"
                        "  IMAP_PASSWORD=your-app-password\n\n"
                        "for gmail, use an app password: https://myaccount.google.com/apppasswords",
                display_raw=True,
            )

        try:
            return self._check_inbox(server, user, password)
        except Exception as e:
            return SkillResult(content=f"email error: {e}", display_raw=True)

    def _check_inbox(self, server: str, user: str, password: str) -> SkillResult:
        mail = imaplib.IMAP4_SSL(server)
        mail.login(user, password)
        mail.select("INBOX")

        # Get unread messages
        status, data = mail.search(None, "UNSEEN")
        if status != "OK":
            mail.logout()
            return SkillResult(content="couldn't search inbox", display_raw=True)

        msg_ids = data[0].split()
        total_unread = len(msg_ids)

        if total_unread == 0:
            mail.logout()
            return SkillResult(content="inbox clear — no unread emails", inject_as_context=True)

        # Fetch latest 10 unread
        summaries = []
        for msg_id in msg_ids[-10:]:
            try:
                status, msg_data = mail.fetch(msg_id, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
                if status != "OK":
                    continue

                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)

                subject = self._decode_header(msg.get("Subject", "(no subject)"))
                sender = self._decode_header(msg.get("From", "unknown"))
                date = msg.get("Date", "")

                # Clean up sender
                if "<" in sender:
                    sender = sender.split("<")[0].strip().strip('"')

                summaries.append(f"  {sender}: {subject}")
            except Exception:
                continue

        mail.logout()

        content = f"inbox: {total_unread} unread\n" + "\n".join(summaries)
        return SkillResult(content=content, inject_as_context=True)

    @staticmethod
    def _decode_header(val: str) -> str:
        try:
            decoded = decode_header(val)
            parts = []
            for part, charset in decoded:
                if isinstance(part, bytes):
                    parts.append(part.decode(charset or "utf-8", errors="replace"))
                else:
                    parts.append(part)
            return " ".join(parts)
        except Exception:
            return val


# ── Morning Briefing ───────────────────────────────────────────────

class BriefingSkill(Skill):
    """
    Morning briefing — aggregates info from multiple sources into
    a single context dump for the LLM to present naturally.
    """
    name = "briefing"
    description = "Morning briefing — weather, calendar, emails, system"
    triggers = [
        "briefing", "morning", "good morning", "brief me",
        "what's up", "what did i miss", "daily report",
    ]
    priority = 72

    def can_handle(self, query: str) -> float:
        q = query.lower()
        if any(p in q for p in ["morning briefing", "brief me", "good morning",
                                 "daily report", "what did i miss", "what's the plan"]):
            return 0.9
        return super().can_handle(q)

    def execute(self, query: str, context: dict) -> SkillResult:
        parts = []
        now = datetime.datetime.now()

        # Time
        parts.append(f"[TIME] {now.strftime('%A, %B %d, %Y — %H:%M')}")

        # System status
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.5)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            parts.append(
                f"[SYSTEM] cpu={cpu}% | ram={mem.percent}% ({round(mem.available/1024**3,1)}GB free) | "
                f"disk={disk.percent}%"
            )
        except Exception:
            pass

        # Weather (quick attempt via wttr.in)
        try:
            r = subprocess.run(
                "curl -s --max-time 3 'wttr.in/?format=%C+%t+%w' 2>/dev/null",
                shell=True, capture_output=True, text=True, timeout=5,
            )
            if r.stdout.strip() and "Unknown" not in r.stdout:
                parts.append(f"[WEATHER] {r.stdout.strip()}")
        except Exception:
            pass

        # Calendar (try gcalcli or calcurse)
        cal = CalendarSkill()
        cal_result = cal.execute("today's schedule", {})
        if cal_result.content and "not configured" not in cal_result.content.lower() and "not found" not in cal_result.content.lower():
            parts.append(cal_result.content)

        # Email (if configured)
        email_skill = EmailSkill()
        email_result = email_skill.execute("check inbox", {})
        if "not configured" not in email_result.content:
            parts.append(f"[EMAIL] {email_result.content}")

        # Git (latest repo activity)
        git_skill = GitSkill()
        git_result = git_skill.execute("git log 5", {})
        if "no git" not in git_result.content.lower():
            parts.append(f"[GIT] {git_result.content}")

        return SkillResult(
            content="\n\n".join(parts),
            inject_as_context=True,
        )


# ── Automation Management Skill ────────────────────────────────────

class AutomationSkill(Skill):
    """Manage automations via natural language."""
    name = "automate"
    description = "Create, list, and manage automations"
    triggers = [
        "automate", "automation", "schedule", "every day",
        "every morning", "every hour", "when idle", "cron",
        "recurring", "repeat",
    ]
    priority = 68

    _engine = None

    def _get_engine(self):
        if self._engine is None:
            from rokan_core.automations import AutomationEngine
            self._engine = AutomationEngine()
        return self._engine

    def can_handle(self, query: str) -> float:
        q = query.lower()
        if q.startswith("/automate") or q.startswith("/automation"):
            return 1.0
        if any(p in q for p in ["every day at", "every morning", "every hour",
                                 "every week", "when idle", "when cpu", "when disk",
                                 "list automations", "my automations"]):
            return 0.9
        if re.match(r'every\s+\d+\s+(min|hour|sec)', q):
            return 0.9
        return super().can_handle(q)

    def execute(self, query: str, context: dict) -> SkillResult:
        q = query.lower().strip()
        for prefix in ("/automate ", "/automation "):
            if q.startswith(prefix):
                q = q[len(prefix):]
                break

        engine = self._get_engine()

        # List automations
        if q in ("list", "ls", "show", "") or "list" in q or "show" in q:
            autos = engine.list_all()
            if not autos:
                return SkillResult(content="no automations set", display_raw=True)
            lines = [f"automations ({len(autos)}):"]
            for a in autos:
                status = "on" if a.enabled else "off"
                lines.append(f"  [{a.id}] [{status}] {a.name} -> {a.action}")
            return SkillResult(content="\n".join(lines), display_raw=True)

        # Remove automation
        m = re.match(r'(?:remove|delete|rm)\s+(\d+)', q)
        if m:
            auto_id = int(m.group(1))
            if engine.remove(auto_id):
                return SkillResult(content=f"automation #{auto_id} removed", display_raw=True)
            return SkillResult(content=f"automation #{auto_id} not found", display_raw=True)

        # Toggle
        m = re.match(r'(?:enable|on)\s+(\d+)', q)
        if m:
            engine.toggle(int(m.group(1)), True)
            return SkillResult(content=f"automation #{m.group(1)} enabled", display_raw=True)
        m = re.match(r'(?:disable|off)\s+(\d+)', q)
        if m:
            engine.toggle(int(m.group(1)), False)
            return SkillResult(content=f"automation #{m.group(1)} disabled", display_raw=True)

        # Create new automation
        auto = engine.parse_and_add(q)
        if auto:
            return SkillResult(
                content=f"automation created: [{auto.id}] {auto.name} -> {auto.action}",
                display_raw=True,
            )

        return SkillResult(
            content="couldn't parse automation. try:\n"
                    "  every day at 9am, check email\n"
                    "  every 30 minutes, check system status\n"
                    "  when cpu above 90%, alert me\n"
                    "  when idle for 10 minutes, lock screen",
            display_raw=True,
        )


# ── Registry ───────────────────────────────────────────────────────

def create_integration_skills() -> list[Skill]:
    """Create all integration skills."""
    return [
        GitSkill(),
        CalendarSkill(),
        EmailSkill(),
        BriefingSkill(),
        AutomationSkill(),
    ]
