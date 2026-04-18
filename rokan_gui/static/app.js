let currentMode = "normal";
let voiceEnabled = true;
let isStreaming = false;

// boot

async function boot() {
  const area = document.getElementById("boot-area");

  const line = (t, cls) => {
    const d = document.createElement("div");
    d.className = "boot-line" + (cls ? " " + cls : "");
    d.textContent = t;
    area.appendChild(d);
  };

  try {
    const res = await fetch("/api/status");
    const data = await res.json();

    for (const [slot, on] of Object.entries(data.models)) {
      line(`${slot.padEnd(12)} ${on ? "ok" : "--"}`);
    }
    line(`memory       ${data.memory.total_memories}`);
    line(`skills       ${data.skills.length}`);
    line("");
    line("ready", "hi");

    updateSidebar(data);
  } catch (e) {
    line("connecting...");
  }

  setInterval(pollStatus, 3000);
  document.getElementById("input").focus();
}

// status

async function pollStatus() {
  try {
    const res = await fetch("/api/status");
    updateSidebar(await res.json());
  } catch (e) {}
}

function updateSidebar(data) {
  const sys = data.system || {};

  setStat("cpu", sys.cpu || 0);
  setStat("ram", sys.ram_percent || 0);
  setStat("disk", sys.disk_percent || 0);

  for (const [slot, on] of Object.entries(data.models || {})) {
    const el = document.getElementById("model-" + slot);
    if (el) el.className = "model-row" + (on ? " online" : "");
  }

  const mem = data.memory || {};
  document.getElementById("mem-count").textContent = mem.total_memories || 0;
  document.getElementById("session-count").textContent = (mem.sessions || 0) + " sessions";

  const alerts = data.alerts || [];
  const section = document.getElementById("alerts-section");
  const list = document.getElementById("alerts-list");
  if (alerts.length) {
    section.style.display = "";
    list.innerHTML = alerts.slice(0, 3).map(a =>
      '<div class="alert-item">' + esc(a.message) + "</div>"
    ).join("");
  } else {
    section.style.display = "none";
  }
}

function setStat(name, pct) {
  const fill = document.getElementById(name + "-fill");
  const val = document.getElementById(name + "-val");
  if (fill) {
    fill.style.width = Math.min(pct, 100) + "%";
    fill.className = "stat-fill" + (pct > 90 ? " crit" : pct > 75 ? " warn" : "");
  }
  if (val) val.textContent = Math.round(pct) + "%";
}

// chat

function handleKey(e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
  const ta = e.target;
  ta.style.height = "auto";
  ta.style.height = Math.min(ta.scrollHeight, 160) + "px";
}

async function sendMessage() {
  const input = document.getElementById("input");
  const text = input.value.trim();
  if (!text || isStreaming) return;

  input.value = "";
  input.style.height = "auto";

  addMsg(text, "user");

  const payload = {
    message: text,
    think: currentMode === "think",
    code: currentMode === "code",
    fast: currentMode === "fast",
  };

  isStreaming = true;
  document.getElementById("send-btn").disabled = true;

  let aiEl = null, reasonEl = null;
  let full = "", reasoning = "";

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buf += decoder.decode(value, { stream: true });
      const lines = buf.split("\n");
      buf = lines.pop() || "";

      for (const ln of lines) {
        if (!ln.startsWith("data: ")) continue;
        const raw = ln.slice(6);
        if (raw === "[DONE]") break;

        try {
          const c = JSON.parse(raw);

          if (c.type === "reasoning") {
            reasoning += c.text;
            if (!reasonEl) reasonEl = addMsg(reasoning, "reasoning");
            else reasonEl.textContent = reasoning;
            scroll();
          } else if (c.type === "content") {
            full += c.text;
            if (!aiEl) aiEl = addMsg(full, "ai");
            else aiEl.innerHTML = md(full);
            scroll();
          } else if (c.type === "error") {
            addMsg(c.text, "error");
          } else if (c.type === "system") {
            addMsg(c.text, "system");
          } else if (c.type === "skill") {
            addMsg(c.text, "ai");
            full = c.text;
          }
        } catch (e) {}
      }
    }

    if (full && voiceEnabled) {
      fetch("/api/voice/speak", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: full }),
      }).catch(() => {});
    }
  } catch (e) {
    addMsg(e.message, "error");
  }

  isStreaming = false;
  document.getElementById("send-btn").disabled = false;
  document.getElementById("input").focus();
}

function addMsg(text, type) {
  const chat = document.getElementById("chat");
  const div = document.createElement("div");
  div.className = "message " + type;
  div.innerHTML = type === "ai" ? md(text) : esc(text);
  chat.appendChild(div);
  scroll();
  return div;
}

function scroll() {
  const c = document.getElementById("chat");
  c.scrollTop = c.scrollHeight;
}

// markdown (minimal)

function md(text) {
  let h = esc(text);
  h = h.replace(/```(\w*)\n([\s\S]*?)```/g, (_, l, c) => "<pre><code>" + c.trim() + "</code></pre>");
  h = h.replace(/`([^`]+)`/g, "<code>$1</code>");
  h = h.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  h = h.replace(/\*(.+?)\*/g, "<em>$1</em>");
  return h;
}

function esc(t) {
  const d = document.createElement("div");
  d.textContent = t;
  return d.innerHTML;
}

// mode

function setMode(mode) {
  currentMode = mode;
  document.querySelectorAll(".mode-btn").forEach(b => {
    b.classList.toggle("active", b.dataset.mode === mode);
  });
}

// actions

function toggleVoice() {
  voiceEnabled = !voiceEnabled;
  document.getElementById("voice-btn").textContent = "voice: " + (voiceEnabled ? "on" : "off");
}

async function clearChat() {
  const chat = document.getElementById("chat");
  chat.innerHTML = '<div id="boot-area"><div class="boot-line hi">cleared</div></div>';
  await fetch("/api/clear", { method: "POST" });
}

document.addEventListener("DOMContentLoaded", boot);
