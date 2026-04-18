/* ═══════════════════════════════════════════════════════════════
   ROKAN — Desktop App Frontend
   SSE streaming, boot sequence, system monitoring.
   ═══════════════════════════════════════════════════════════════ */

let currentMode = "normal";
let voiceEnabled = true;
let isStreaming = false;

// ── Boot Sequence ────────────────────────────────────────────────

async function boot() {
  const area = document.getElementById("boot-area");
  const lines = [
    "[BOOT] Initializing neural link...",
    "[BOOT] Loading agent core...",
  ];

  for (const line of lines) {
    await addBootLine(area, line, 80);
  }

  // Fetch real status
  try {
    const res = await fetch("/api/status");
    const data = await res.json();

    if (data.llm_online) {
      await addBootLine(area, "[BOOT] LLM connection — ESTABLISHED", 60, "ok");
      for (const [slot, online] of Object.entries(data.models)) {
        const tag = online ? "ONLINE" : "OFFLINE";
        const cls = online ? "ok" : "";
        await addBootLine(area, `[BOOT]   ${slot.toUpperCase().padEnd(12)} — ${tag}`, 40, cls);
      }
    } else {
      await addBootLine(area, "[BOOT] LLM — WAITING (set NVIDIA_API_KEY)", 60);
    }

    await addBootLine(area, `[BOOT] Memory — ${data.memory.total_memories} entries, ${data.memory.sessions} sessions`, 60);
    await addBootLine(area, `[BOOT] Skills — ${data.skills.length} active: ${data.skills.map(s => s.name).join(", ")}`, 60);
    await addBootLine(area, "[BOOT] Proactive monitoring — ACTIVE", 60);
    await addBootLine(area, "[BOOT] Voice synthesis — ONLINE", 60);
    await addBootLine(area, "", 100);
    await addBootLine(area, "[SYS]  I'm online. What do you need?", 0, "bright");

    // Update sidebar
    updateSidebar(data);

  } catch (e) {
    await addBootLine(area, `[BOOT] Status check failed: ${e.message}`, 60);
  }

  // Start periodic status updates
  setInterval(pollStatus, 3000);

  document.getElementById("input").focus();
}

function addBootLine(area, text, delay, cls = "") {
  return new Promise(resolve => {
    setTimeout(() => {
      const div = document.createElement("div");
      div.className = `boot-line ${cls}`;
      div.textContent = text;
      area.appendChild(div);
      scrollToBottom();
      resolve();
    }, delay);
  });
}

// ── Status Polling ───────────────────────────────────────────────

async function pollStatus() {
  try {
    const res = await fetch("/api/status");
    const data = await res.json();
    updateSidebar(data);
  } catch (e) { /* silent */ }
}

function updateSidebar(data) {
  const sys = data.system || {};

  // System stats
  updateStat("cpu", sys.cpu || 0, `${sys.cpu || 0}%`);
  updateStat("ram", sys.ram_percent || 0, `${sys.ram_percent || 0}%`);
  updateStat("disk", sys.disk_percent || 0, `${sys.disk_percent || 0}%`);

  // Models
  for (const [slot, online] of Object.entries(data.models || {})) {
    const el = document.getElementById(`model-${slot}`);
    if (el) {
      el.className = `model-row ${online ? "online" : ""}`;
    }
  }

  // Memory
  const mem = data.memory || {};
  document.getElementById("mem-count").textContent = `${mem.total_memories || 0} memories`;
  document.getElementById("session-count").textContent = `${mem.sessions || 0} sessions`;

  // Alerts
  const alerts = data.alerts || [];
  const section = document.getElementById("alerts-section");
  const list = document.getElementById("alerts-list");
  if (alerts.length > 0) {
    section.style.display = "";
    list.innerHTML = alerts.slice(0, 3).map(a =>
      `<div class="alert-item ${a.severity}">${a.message}</div>`
    ).join("");
  } else {
    section.style.display = "none";
  }
}

function updateStat(name, pct, label) {
  const fill = document.getElementById(`${name}-fill`);
  const val = document.getElementById(`${name}-val`);
  if (fill) {
    fill.style.width = `${Math.min(pct, 100)}%`;
    fill.className = `stat-fill${pct > 90 ? " crit" : pct > 75 ? " warn" : ""}`;
  }
  if (val) val.textContent = label;
}

// ── Chat ─────────────────────────────────────────────────────────

function handleKey(e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
  // Auto-resize textarea
  const ta = e.target;
  ta.style.height = "auto";
  ta.style.height = Math.min(ta.scrollHeight, 180) + "px";
}

async function sendMessage() {
  const input = document.getElementById("input");
  const text = input.value.trim();
  if (!text || isStreaming) return;

  input.value = "";
  input.style.height = "auto";

  // Add user message
  addMessage(text, "user");

  // Determine mode flags
  const payload = {
    message: text,
    think: currentMode === "think",
    code: currentMode === "code",
    fast: currentMode === "fast",
  };

  // Start streaming
  isStreaming = true;
  document.getElementById("send-btn").disabled = true;

  let aiMsg = null;
  let reasonMsg = null;
  let fullResponse = "";
  let fullReasoning = "";

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const payload = line.slice(6);
        if (payload === "[DONE]") break;

        try {
          const chunk = JSON.parse(payload);

          if (chunk.type === "reasoning") {
            fullReasoning += chunk.text;
            if (!reasonMsg) {
              reasonMsg = addMessage(fullReasoning, "reasoning");
            } else {
              reasonMsg.textContent = fullReasoning;
            }
            scrollToBottom();
          }
          else if (chunk.type === "content") {
            fullResponse += chunk.text;
            if (!aiMsg) {
              aiMsg = addMessage(fullResponse, "ai");
            } else {
              aiMsg.innerHTML = formatMarkdown(fullResponse);
            }
            scrollToBottom();
          }
          else if (chunk.type === "error") {
            addMessage(chunk.text, "error");
          }
          else if (chunk.type === "system") {
            addMessage(chunk.text, "system");
          }
          else if (chunk.type === "skill") {
            addMessage(chunk.text, "ai");
            fullResponse = chunk.text;
          }
        } catch (e) { /* skip bad JSON */ }
      }
    }

    // Voice
    if (fullResponse && voiceEnabled) {
      fetch("/api/voice/speak", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: fullResponse }),
      }).catch(() => {});
    }

  } catch (e) {
    addMessage(`[ERROR] ${e.message}`, "error");
  }

  isStreaming = false;
  document.getElementById("send-btn").disabled = false;
  document.getElementById("input").focus();
}

function addMessage(text, type) {
  const chat = document.getElementById("chat");
  const div = document.createElement("div");
  div.className = `message ${type}`;

  if (type === "ai") {
    div.innerHTML = formatMarkdown(text);
  } else {
    div.textContent = text;
  }

  chat.appendChild(div);
  scrollToBottom();
  return div;
}

function scrollToBottom() {
  const chat = document.getElementById("chat");
  chat.scrollTop = chat.scrollHeight;
}

// ── Markdown-lite ────────────────────────────────────────────────

function formatMarkdown(text) {
  let html = escapeHtml(text);

  // Code blocks
  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) =>
    `<pre><code>${code.trim()}</code></pre>`
  );

  // Inline code
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");

  // Bold
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");

  // Italic
  html = html.replace(/\*(.+?)\*/g, "<em>$1</em>");

  // Links
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');

  return html;
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// ── Mode Selection ───────────────────────────────────────────────

function setMode(mode) {
  currentMode = mode;
  document.querySelectorAll(".mode-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.mode === mode);
  });
}

// ── Actions ──────────────────────────────────────────────────────

function toggleVoice() {
  voiceEnabled = !voiceEnabled;
  const btn = document.getElementById("voice-btn");
  btn.textContent = voiceEnabled ? "🔊 Voice" : "🔇 Muted";
  btn.classList.toggle("active", voiceEnabled);
}

async function clearChat() {
  document.getElementById("chat").innerHTML =
    '<div class="boot-msg"><div class="boot-line bright">[SYS] Chat cleared.</div></div>';
  await fetch("/api/clear", { method: "POST" });
}

// ── Init ─────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", boot);
