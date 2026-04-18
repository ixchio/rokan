"""
Rokan TUI — The System Interface.
F.R.I.D.A.Y.-class ambient intelligence with Solo Leveling aesthetics.
Everything flows through the Agent Core now.
"""

import time
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Header, Footer, Input, Static, Rule
from textual import work

from rokan_core.agent import RokanAgent
from rokan_core.proactive import Alert
from rokan_tui.system_monitor import SystemMonitor
from rokan_tui.voice import RokanVoice

# ── ASCII Boot Logo ──────────────────────────────────────────────────
BOOT_LOGO = """\
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   ██████╗  ██████╗ ██╗  ██╗ █████╗ ███╗   ██╗               ║
║   ██╔══██╗██╔═══██╗██║ ██╔╝██╔══██╗████╗  ██║               ║
║   ██████╔╝██║   ██║█████╔╝ ███████║██╔██╗ ██║               ║
║   ██╔══██╗██║   ██║██╔═██╗ ██╔══██║██║╚██╗██║               ║
║   ██║  ██║╚██████╔╝██║  ██╗██║  ██║██║ ╚████║               ║
║   ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝               ║
║                                                              ║
║   ▸ SYSTEM v2.0           ▸ Ambient Intelligence             ║
║   ▸ The System            ▸ Always watching. Always ready.   ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝"""


def _build_boot_sequence(agent: RokanAgent) -> list[str]:
    """Dynamic boot sequence based on actual system state."""
    lines = ["[BOOT] Initializing neural link..."]

    status = agent.get_model_status()
    if any(status.values()):
        lines.append("[BOOT] LLM connection — ESTABLISHED")
        for slot, ok in status.items():
            tag = "ONLINE" if ok else "OFFLINE"
            lines.append(f"[BOOT]   {slot.upper():12s} — {tag}")
    else:
        lines.append("[BOOT] LLM connection — WAITING (set NVIDIA_API_KEY)")

    lines.append("[BOOT] Memory system — ONLINE (SQLite)")

    mem_stats = agent.memory.stats()
    if mem_stats["total_memories"] > 0:
        lines.append(
            f"[BOOT]   {mem_stats['total_memories']} memories loaded, "
            f"{mem_stats['sessions']} past sessions"
        )

    skills = agent.skills.list_skills()
    lines.append(f"[BOOT] Skills — {len(skills)} active: {', '.join(s['name'] for s in skills)}")
    lines.append("[BOOT] Proactive monitoring — ACTIVE")
    lines.append("[BOOT] Voice synthesis — ONLINE")
    lines.append("[SYS]  I'm online. What do you need?")

    return lines


# ── Widgets ──────────────────────────────────────────────────────────

class StatusPanel(Static):
    """Left sidebar: system stats + model info + skills."""

    def compose(self) -> ComposeResult:
        yield Static("╔══ SYSTEM ══╗", classes="panel-header")
        yield Static("", id="cpu-bar")
        yield Static("", id="ram-bar")
        yield Static("", id="disk-bar")
        yield Rule(line_style="heavy")
        yield Static("╔══ MODELS ══╗", classes="panel-header")
        yield Static("  PRIMARY  Llama-3.3 70B", id="model-label", classes="info-line")
        yield Static("  REASON   GLM 4.7", id="reason-label", classes="info-line")
        yield Static("  FAST     Step 3.5 Flash", id="fast-label", classes="info-line")
        yield Static("  CODE     QwQ 32B", id="code-label", classes="info-line")
        yield Rule(line_style="heavy")
        yield Static("╔══ COMMANDS ══╗", classes="panel-header")
        yield Static("  /think  Deep reasoning", classes="info-line")
        yield Static("  /code   Run code", classes="info-line")
        yield Static("  /fast   Quick answer", classes="info-line")
        yield Static("  /search Web search", classes="info-line")
        yield Static("  /system System info", classes="info-line")
        yield Static("  /memory Memory stats", classes="info-line")
        yield Static("  /skills List skills", classes="info-line")
        yield Static("  /voice  Toggle voice", classes="info-line")
        yield Static("  /clear  Clear chat", classes="info-line")
        yield Static("  Ctrl+Q  Quit", classes="info-line")
        yield Rule(line_style="heavy")
        yield Static("", id="alert-panel")

    def update_stats(self, stats: dict) -> None:
        """Render stat bars with visual meter."""
        try:
            cpu_bar = self._make_bar("CPU", stats["cpu"], stats.get("cpu_cores", ""))
            ram_bar = self._make_bar("RAM", stats["ram"], stats["ram_used"])
            disk_bar = self._make_bar("DSK", stats["disk"], stats["disk_used"])

            self.query_one("#cpu-bar", Static).update(cpu_bar)
            self.query_one("#ram-bar", Static).update(ram_bar)
            self.query_one("#disk-bar", Static).update(disk_bar)
        except Exception:
            pass

    def update_alerts(self, alerts: list[Alert]) -> None:
        """Show proactive alerts in sidebar."""
        try:
            panel = self.query_one("#alert-panel", Static)
            if not alerts:
                panel.update("")
                return

            icons = {"critical": "🔴", "warning": "⚠️", "info": "ℹ️"}
            lines = ["╔══ ALERTS ══╗"]
            for a in alerts[:3]:
                icon = icons.get(a.severity, "•")
                lines.append(f"  {icon} {a.message[:26]}")
            panel.update("\n".join(lines))
        except Exception:
            pass

    @staticmethod
    def _make_bar(label: str, pct: float, detail: str) -> str:
        width = 18
        filled = int(pct / 100 * width)
        empty = width - filled
        char = "█" if pct < 80 else "▓"
        bar = char * filled + "░" * empty
        return f"  {label} [{bar}] {pct:4.0f}%  {detail}"


class ChatMessage(Static):
    """A single message bubble."""
    pass


class ChatArea(VerticalScroll):
    """Scrollable chat region."""

    def add_message(self, text: str, role: str = "rokan") -> "ChatMessage":
        """Mount a new message and scroll down."""
        msg = ChatMessage(text, classes=f"msg msg-{role}")
        self.mount(msg)
        self.scroll_end(animate=False)
        return msg


# ── Main App ─────────────────────────────────────────────────────────

class RokanApp(App):
    """Rokan — The System. F.R.I.D.A.Y.-class ambient intelligence."""

    CSS_PATH = "styles.tcss"
    TITLE = "ROKAN"
    SUB_TITLE = "THE SYSTEM — AMBIENT INTELLIGENCE ACTIVE"

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", show=True),
        Binding("ctrl+l", "clear_chat", "Clear", show=True),
        Binding("ctrl+s", "toggle_sidebar", "Sidebar", show=True),
    ]

    def __init__(self):
        super().__init__()
        # THE BRAIN — everything goes through here now
        self.agent = RokanAgent()
        self.monitor = SystemMonitor()
        self.voice = RokanVoice()
        self.voice_enabled = True

    # ── Layout ───────────────────────────────────────────────────
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="main-layout"):
            yield StatusPanel(id="sidebar")
            with Vertical(id="chat-column"):
                yield ChatArea(id="chat")
                with Container(id="input-bar"):
                    yield Input(
                        placeholder="  ▸ What do you need?",
                        id="prompt",
                    )
        yield Footer()

    # ── Lifecycle ────────────────────────────────────────────────
    def on_mount(self) -> None:
        self.agent.start()
        self.agent.set_alert_callback(self._on_proactive_alert)
        self.monitor.start(callback_func=self._on_stats_update)
        self._boot_sequence()

    def on_unmount(self) -> None:
        self.agent.stop()
        self.monitor.stop()

    @work(thread=True)
    def _boot_sequence(self) -> None:
        """Dynamic boot sequence reflecting actual system state."""
        chat: ChatArea = self.query_one("#chat", ChatArea)
        self.call_from_thread(chat.add_message, BOOT_LOGO, "system")
        time.sleep(0.3)
        for line in _build_boot_sequence(self.agent):
            self.call_from_thread(chat.add_message, line, "boot")
            time.sleep(0.12)
        self.call_from_thread(self.query_one("#prompt", Input).focus)

    # ── Callbacks (from background threads) ──────────────────────
    def _on_stats_update(self, stats: dict) -> None:
        try:
            sidebar = self.query_one("#sidebar", StatusPanel)
            self.call_from_thread(sidebar.update_stats, stats)
            # Also update alerts in sidebar
            alerts = self.agent.get_pending_alerts()
            self.call_from_thread(sidebar.update_alerts, alerts)
        except Exception:
            pass

    def _on_proactive_alert(self, alert: Alert) -> None:
        """Handle proactive alert from agent — show in chat."""
        try:
            chat: ChatArea = self.query_one("#chat", ChatArea)
            icons = {"critical": "🔴", "warning": "⚠️", "info": "ℹ️"}
            icon = icons.get(alert.severity, "•")
            self.call_from_thread(
                chat.add_message,
                f"{icon} [PROACTIVE] {alert.message}",
                "boot",
            )
        except Exception:
            pass

    # ── Input handling ───────────────────────────────────────────
    async def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text:
            return

        prompt_widget = self.query_one("#prompt", Input)
        prompt_widget.value = ""

        # Voice toggle (TUI-only, not agent concern)
        if text == "/voice":
            self.voice_enabled = not self.voice_enabled
            chat = self.query_one("#chat", ChatArea)
            state = "ENABLED" if self.voice_enabled else "DISABLED"
            chat.add_message(f"[SYS] Voice output {state}.", "boot")
            return

        # Determine model mode from prefixes
        use_reasoning = False
        use_code = False
        use_fast = False

        if text.startswith("/think "):
            text = text[7:]
            use_reasoning = True
        elif text.startswith("/fast "):
            text = text[6:]
            use_fast = True

        chat = self.query_one("#chat", ChatArea)
        chat.add_message(f"▸ {text}", "user")

        # Launch streaming worker through the AGENT CORE
        self._stream_reply(text, use_reasoning, use_code, use_fast)

    # ── Streaming worker — now goes through Agent Core ───────────
    @work(exclusive=True, thread=True)
    def _stream_reply(
        self,
        user_input: str,
        use_reasoning: bool = False,
        use_code: bool = False,
        use_fast: bool = False,
    ) -> None:
        chat: ChatArea = self.query_one("#chat", ChatArea)
        full_response = ""
        full_reasoning = ""
        reason_msg: ChatMessage | None = None
        content_msg: ChatMessage | None = None

        try:
            for chunk in self.agent.process(
                user_input,
                use_reasoning=use_reasoning,
                use_code=use_code,
                use_fast=use_fast,
            ):
                ctype = chunk["type"]
                ctext = chunk["text"]

                if ctype == "reasoning":
                    full_reasoning += ctext
                    if reason_msg is None:
                        reason_msg = self.call_from_thread(
                            chat.add_message, full_reasoning, "reasoning"
                        )
                    else:
                        self.call_from_thread(reason_msg.update, full_reasoning)
                        self.call_from_thread(chat.scroll_end, animate=False)

                elif ctype == "content":
                    full_response += ctext
                    if content_msg is None:
                        content_msg = self.call_from_thread(
                            chat.add_message, full_response, "rokan"
                        )
                    else:
                        self.call_from_thread(content_msg.update, full_response)
                        self.call_from_thread(chat.scroll_end, animate=False)

                elif ctype == "error":
                    self.call_from_thread(chat.add_message, ctext, "error")
                    return

                elif ctype == "system":
                    self.call_from_thread(chat.add_message, ctext, "boot")

                elif ctype == "skill":
                    self.call_from_thread(chat.add_message, ctext, "rokan")
                    full_response = ctext

        except Exception as exc:
            self.call_from_thread(
                chat.add_message, f"[ERROR] {exc}", "error"
            )
            return

        if full_response and self.voice_enabled:
            self.voice.speak(full_response)

    # ── Actions ──────────────────────────────────────────────────
    def action_clear_chat(self) -> None:
        chat = self.query_one("#chat", ChatArea)
        chat.remove_children()
        chat.add_message("[SYS] Chat cleared.", "boot")
        self.agent.history.clear()

    def action_toggle_sidebar(self) -> None:
        sidebar = self.query_one("#sidebar")
        sidebar.display = not sidebar.display


# ── Entry ────────────────────────────────────────────────────────────
def run():
    app = RokanApp()
    app.run()

if __name__ == "__main__":
    run()
