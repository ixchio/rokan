"""
Rokan GUI Server — Flask backend powering the desktop app.
SSE streaming for chat, REST for everything else.
"""

import json
import os
import threading
import time
import uuid
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_from_directory

from rokan_core.agent import RokanAgent

# ── Flask App ────────────────────────────────────────────────────────

STATIC = Path(__file__).parent / "static"

app = Flask(__name__, static_folder=str(STATIC), static_url_path="/static")
app.config["SECRET_KEY"] = uuid.uuid4().hex

# Global agent (initialized on first request or at start)
_agent: RokanAgent | None = None
_agent_lock = threading.Lock()


def get_agent() -> RokanAgent:
    global _agent
    if _agent is None:
        with _agent_lock:
            if _agent is None:
                _agent = RokanAgent()
                _agent.start()
    return _agent


# ── Routes ───────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(str(STATIC), "index.html")


@app.route("/api/avatar")
def avatar():
    """Serve user avatar from ~/.rokan/avatar.png or default."""
    user_avatar = Path.home() / ".rokan" / "avatar.png"
    if user_avatar.exists():
        return send_from_directory(str(user_avatar.parent), user_avatar.name)

    # Check for jpg/webp too
    for ext in ("jpg", "jpeg", "webp", "gif"):
        alt = user_avatar.with_suffix("." + ext)
        if alt.exists():
            return send_from_directory(str(alt.parent), alt.name)

    # Default: serve built-in placeholder
    default = STATIC / "avatar-default.png"
    if default.exists():
        return send_from_directory(str(STATIC), "avatar-default.png")

    # Generate a minimal SVG circle as last resort
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">'
        '<circle cx="50" cy="50" r="48" fill="#1a1a1a" stroke="#333" stroke-width="1"/>'
        '<text x="50" y="58" text-anchor="middle" fill="#555" '
        'font-family="monospace" font-size="14">R</text></svg>'
    )
    return Response(svg, mimetype="image/svg+xml")


@app.route("/api/chat", methods=["POST"])
def chat():
    """Stream a chat response via SSE."""
    data = request.get_json(force=True)
    user_input = data.get("message", "").strip()
    use_reasoning = data.get("think", False)
    use_code = data.get("code", False)
    use_fast = data.get("fast", False)

    if not user_input:
        return jsonify({"error": "Empty message"}), 400

    def generate():
        agent = get_agent()
        try:
            for chunk in agent.process(
                user_input,
                use_reasoning=use_reasoning,
                use_code=use_code,
                use_fast=use_fast,
            ):
                payload = json.dumps(chunk)
                yield f"data: {payload}\n\n"
        except Exception as exc:
            err = json.dumps({"type": "error", "text": str(exc)})
            yield f"data: {err}\n\n"
        yield "data: [DONE]\n\n"

    return Response(generate(), mimetype="text/event-stream")


@app.route("/api/status")
def status():
    agent = get_agent()
    model_status = agent.get_model_status()
    mem_stats = agent.memory.stats()
    skills = agent.skills.list_skills()

    sys_info = {}
    try:
        import psutil

        def gb(b): return round(b / (1024**3), 1)

        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        sys_info = {
            "cpu": round(cpu, 1),
            "cpu_cores": psutil.cpu_count(),
            "ram_percent": round(mem.percent, 1),
            "ram_used_gb": gb(mem.used),
            "ram_total_gb": gb(mem.total),
            "ram_free_gb": gb(mem.available),
            "disk_percent": round(disk.percent, 1),
            "disk_used_gb": gb(disk.used),
            "disk_total_gb": gb(disk.total),
        }
    except ImportError:
        pass

    return jsonify({
        "models": model_status,
        "llm_online": any(model_status.values()),
        "memory": mem_stats,
        "skills": skills,
        "system": sys_info,
        "screen": agent.get_screen_state(),
        "voice": agent.get_voice_status(),
        "automations": len(agent.get_automations()),
        "alerts": [
            {"type": a.type, "severity": a.severity, "message": a.message}
            for a in agent.get_pending_alerts()
        ],
    })


@app.route("/api/remember", methods=["POST"])
def remember():
    data = request.get_json(force=True)
    fact = data.get("fact", "").strip()
    if not fact:
        return jsonify({"error": "Empty fact"}), 400
    agent = get_agent()
    mid = agent.memory.store(fact, tier="semantic")
    return jsonify({"ok": True, "id": mid, "fact": fact})


@app.route("/api/recall", methods=["POST"])
def recall():
    data = request.get_json(force=True)
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"error": "Empty query"}), 400
    agent = get_agent()
    results = agent.memory.recall(query, limit=10)
    return jsonify({"results": results})


@app.route("/api/history")
def history():
    """Return recent conversation for current session (UI reload)."""
    agent = get_agent()
    messages = agent.memory.get_conversation(agent.session_id, limit=50)
    return jsonify({"messages": messages, "session_id": agent.session_id})


@app.route("/api/voice/speak", methods=["POST"])
def speak():
    data = request.get_json(force=True)
    text = data.get("text", "")

    def _speak():
        try:
            from rokan_tui.voice import RokanVoice
            voice = RokanVoice()
            voice.speak(text)
        except Exception:
            pass

    threading.Thread(target=_speak, daemon=True).start()
    return jsonify({"ok": True})


@app.route("/api/clear", methods=["POST"])
def clear():
    agent = get_agent()
    agent.history.clear()
    return jsonify({"ok": True})


@app.route("/api/screen")
def screen_state():
    """Current screen awareness state."""
    agent = get_agent()
    return jsonify(agent.get_screen_state())


@app.route("/api/voice/status")
def voice_status():
    agent = get_agent()
    return jsonify(agent.get_voice_status())


@app.route("/api/voice/start", methods=["POST"])
def voice_start():
    agent = get_agent()
    agent.start_voice()
    return jsonify({"ok": True})


@app.route("/api/voice/stop", methods=["POST"])
def voice_stop():
    agent = get_agent()
    agent.stop_voice()
    return jsonify({"ok": True})


@app.route("/api/voice/record", methods=["POST"])
def voice_record():
    """Record from mic, transcribe, and process. Returns transcript + response."""
    agent = get_agent()
    if not agent.voice or not agent.voice.available:
        return jsonify({"error": "voice not available"}), 400

    data = request.get_json(force=True)
    duration = data.get("duration", 5.0)

    transcript = agent.voice.record_and_transcribe(duration)
    if not transcript:
        return jsonify({"transcript": "", "response": ""})

    # Process through agent
    full_response = ""
    for chunk in agent.process(transcript):
        if chunk["type"] in ("content", "skill"):
            full_response += chunk["text"]

    # Speak the response
    if full_response and agent.voice:
        agent.voice.speak_async(full_response)

    return jsonify({
        "transcript": transcript,
        "response": full_response,
    })


@app.route("/api/automations")
def list_automations():
    agent = get_agent()
    return jsonify({"automations": agent.get_automations()})


@app.route("/api/automations", methods=["POST"])
def add_automation():
    agent = get_agent()
    data = request.get_json(force=True)
    text = data.get("text", "").strip()
    if not text or not agent.automations:
        return jsonify({"error": "empty or automations unavailable"}), 400

    auto = agent.automations.parse_and_add(text)
    if auto:
        return jsonify({
            "ok": True,
            "automation": {"id": auto.id, "name": auto.name, "action": auto.action},
        })
    return jsonify({"error": "couldn't parse automation"}), 400


@app.route("/api/automations/<int:auto_id>", methods=["DELETE"])
def delete_automation(auto_id):
    agent = get_agent()
    if agent.automations and agent.automations.remove(auto_id):
        return jsonify({"ok": True})
    return jsonify({"error": "not found"}), 404


# ── Run ──────────────────────────────────────────────────────────────

def run_server(port: int = 18991, debug: bool = False):
    """Start the Flask server."""
    app.run(host="127.0.0.1", port=port, debug=debug, threaded=True)


def start_server_thread(port: int = 18991) -> threading.Thread:
    """Start server in a background thread. Returns the thread."""
    t = threading.Thread(
        target=run_server, args=(port,), daemon=True, name="rokan-server"
    )
    t.start()
    # Wait for server to be ready
    import urllib.request
    for _ in range(30):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status", timeout=1)
            break
        except Exception:
            time.sleep(0.2)
    return t


# Allow running as: python -m rokan_gui.server
if __name__ == "__main__":
    run_server()
