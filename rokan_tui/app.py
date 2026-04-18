"""
Rokan TUI — The Player Interface
Solo Leveling System Window aesthetic. NVIDIA NIM backbone.
"""

import time
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Header, Footer, Input, Static, Rule
from textual.message import Message as TMessage
from textual import work

from rokan_tui.nvidia_client import NvidiaNIMClient
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
║   ▸ SYSTEM v2.0           ▸ NVIDIA NIM ONLINE                ║
║   ▸ The Player            ▸ Awaiting orders.                 ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝"""

BOOT_SEQUENCE = [
    "[BOOT] Initializing neural link...",
    "[BOOT] NVIDIA NIM connection — ESTABLISHED",
    "[BOOT] Model: meta/llama-3.3-70b-instruct — LOADED",
    "[BOOT] Reasoning: z-ai/glm4.7 — STANDBY",
    "[BOOT] Voice synthesis — ONLINE",
    "[BOOT] System monitors — ACTIVE",
    "[SYS]  I am Rokan. Command me.",
]


# ── Widgets ──────────────────────────────────────────────────────────

class StatusPanel(Static):
    """Left sidebar: system stats + model info."""

    def compose(self) -> ComposeResult:
        yield Static("╔══ SYSTEM ══╗", classes="panel-header")
        yield Static("", id="cpu-bar")
        yield Static("", id="ram-bar")
        yield Static("", id="disk-bar")
        yield Rule(line_style="heavy")
        yield Static("╔══ NVIDIA NIM ══╗", classes="panel-header")
        yield Static("  MODEL   Llama-3.3 70B", id="model-label", classes="info-line")
        yield Static("  REASON  GLM 4.7", id="reason-label", classes="info-line")
        yield Static("  FAST    Step 3.5 Flash", id="fast-label", classes="info-line")
        yield Static("  CODE    QwQ 32B", id="code-label", classes="info-line")
        yield Rule(line_style="heavy")
        yield Static("╔══ CONTROLS ══╗", classes="panel-header")
        yield Static("  /think  Deep reasoning", classes="info-line")
        yield Static("  /code   Code model", classes="info-line")
        yield Static("  /fast   Quick answer", classes="info-line")
        yield Static("  /voice  Toggle voice", classes="info-line")
        yield Static("  /clear  Clear chat", classes="info-line")
        yield Static("  Ctrl+Q  Quit", classes="info-line")

    def update_stats(self, stats: dict) -> None:
        """Render stat bars with visual meter."""
        try:
            cpu = stats["cpu"]
            ram = stats["ram"]
            disk = stats["disk"]

            cpu_bar = self._make_bar("CPU", cpu, stats.get("cpu_cores", ""))
            ram_bar = self._make_bar("RAM", ram, stats["ram_used"])
            disk_bar = self._make_bar("DSK", disk, stats["disk_used"])

            self.query_one("#cpu-bar", Static).update(cpu_bar)
            self.query_one("#ram-bar", Static).update(ram_bar)
            self.query_one("#disk-bar", Static).update(disk_bar)
        except Exception:
            pass

    @staticmethod
    def _make_bar(label: str, pct: float, detail: str) -> str:
        width = 18
        filled = int(pct / 100 * width)
        empty = width - filled
        char = "█" if pct < 80 else "▓"
        bar = char * filled + "░" * empty
        color_tag = "danger" if pct > 80 else ""
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
    """Rokan — The Player."""

    CSS_PATH = "styles.tcss"
    TITLE = "ROKAN"
    SUB_TITLE = "THE PLAYER — SYSTEM ACTIVE"

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", show=True),
        Binding("ctrl+l", "clear_chat", "Clear", show=True),
        Binding("ctrl+s", "toggle_sidebar", "Sidebar", show=True),
    ]

    def __init__(self):
        super().__init__()
        self.nim = NvidiaNIMClient()
        self.monitor = SystemMonitor()
        self.voice = RokanVoice()
        self.voice_enabled = True
        self.history: list[dict] = []
        self._current_stream_msg: ChatMessage | None = None
        self._current_reason_msg: ChatMessage | None = None

    # ── Layout ───────────────────────────────────────────────────
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="main-layout"):
            yield StatusPanel(id="sidebar")
            with Vertical(id="chat-column"):
                yield ChatArea(id="chat")
                with Container(id="input-bar"):
                    yield Input(
                        placeholder="  ▸ Awaiting command...",
                        id="prompt",
                    )
        yield Footer()

    # ── Lifecycle ────────────────────────────────────────────────
    def on_mount(self) -> None:
        self.monitor.start(callback_func=self._on_stats_update)
        self._boot_sequence()

    def on_unmount(self) -> None:
        self.monitor.stop()

    @work(thread=True)
    def _boot_sequence(self) -> None:
        """Type-out effect for the boot log."""
        chat: ChatArea = self.query_one("#chat", ChatArea)
        self.call_from_thread(chat.add_message, BOOT_LOGO, "system")
        time.sleep(0.3)
        for line in BOOT_SEQUENCE:
            self.call_from_thread(chat.add_message, line, "boot")
            time.sleep(0.15)
        self.call_from_thread(self.query_one("#prompt", Input).focus)

    # ── Stats callback (from thread) ────────────────────────────
    def _on_stats_update(self, stats: dict) -> None:
        try:
            self.call_from_thread(
                self.query_one("#sidebar", StatusPanel).update_stats, stats
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

        # ── Slash commands ──
        if text == "/clear":
            self.action_clear_chat()
            return
        if text == "/voice":
            self.voice_enabled = not self.voice_enabled
            chat = self.query_one("#chat", ChatArea)
            state = "ENABLED" if self.voice_enabled else "DISABLED"
            chat.add_message(f"[SYS] Voice output {state}.", "boot")
            return

        # ── Determine model mode ──
        use_reasoning = False
        use_code = False
        use_fast = False

        if text.startswith("/think "):
            text = text[7:]
            use_reasoning = True
        elif text.startswith("/code "):
            text = text[6:]
            use_code = True
        elif text.startswith("/fast "):
            text = text[6:]
            use_fast = True

        chat = self.query_one("#chat", ChatArea)
        chat.add_message(f"▸ {text}", "user")

        self.history.append({"role": "user", "content": text})

        # Launch streaming worker
        self._stream_reply(use_reasoning, use_code, use_fast)

    # ── Streaming worker ─────────────────────────────────────────
    @work(exclusive=True, thread=True)
    def _stream_reply(
        self,
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
            for chunk in self.nim.chat_stream(
                self.history,
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

        except Exception as exc:
            self.call_from_thread(
                chat.add_message, f"[ERROR] {exc}", "error"
            )
            return

        if full_response:
            self.history.append({"role": "assistant", "content": full_response})
            if self.voice_enabled:
                self.voice.speak(full_response)

    # ── Actions ──────────────────────────────────────────────────
    def action_clear_chat(self) -> None:
        chat = self.query_one("#chat", ChatArea)
        chat.remove_children()
        chat.add_message("[SYS] Chat cleared.", "boot")
        self.history.clear()

    def action_toggle_sidebar(self) -> None:
        sidebar = self.query_one("#sidebar")
        sidebar.display = not sidebar.display


# ── Entry ────────────────────────────────────────────────────────────
def run():
    app = RokanApp()
    app.run()

if __name__ == "__main__":
    run()
