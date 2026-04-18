"""
Rokan Deep System Introspection — Full kernel-level awareness.

This is what makes Rokan see EVERYTHING on your machine.
Not just "CPU 22%" — but which process is eating it, what network
connections are open, what USB devices are plugged in, what services
crashed, what's in the journal, what files changed, battery state,
GPU usage, temperatures, and more.

Reads from: /proc, /sys, psutil, systemctl, journalctl, ss, lsblk,
upower, sensors, dmesg. All as regular user — no root needed for reads.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


def _run(cmd: str, timeout: int = 5) -> str:
    """Run a command and return stdout. Never raises."""
    try:
        r = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout,
        )
        return r.stdout.strip()
    except Exception:
        return ""


# ── Process Intelligence ─────────────────────────────────────────

def get_top_processes(n: int = 10, sort_by: str = "memory") -> list[dict]:
    """Top N processes by CPU or memory. Uses psutil."""
    try:
        import psutil
    except ImportError:
        return []

    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent",
                                   "memory_info", "create_time", "status", "username"]):
        try:
            info = p.info
            procs.append({
                "pid": info["pid"],
                "name": info["name"],
                "cpu": round(info.get("cpu_percent", 0) or 0, 1),
                "mem_pct": round(info.get("memory_percent", 0) or 0, 1),
                "mem_mb": round((info.get("memory_info") and info["memory_info"].rss or 0) / 1024 / 1024, 1),
                "user": info.get("username", ""),
                "status": info.get("status", ""),
                "uptime_min": round((time.time() - (info.get("create_time") or time.time())) / 60, 1),
            })
        except Exception:
            continue

    key = "mem_pct" if sort_by == "memory" else "cpu"
    procs.sort(key=lambda x: x[key], reverse=True)
    return procs[:n]


def get_process_tree() -> str:
    """Process tree (pstree-style)."""
    return _run("pstree -U --compact-not 2>/dev/null || ps auxf 2>/dev/null | head -40")


def find_process(name: str) -> list[dict]:
    """Find processes by name."""
    try:
        import psutil
    except ImportError:
        return []

    results = []
    q = name.lower()
    for p in psutil.process_iter(["pid", "name", "cmdline", "cpu_percent", "memory_percent"]):
        try:
            info = p.info
            pname = (info.get("name") or "").lower()
            cmdline = " ".join(info.get("cmdline") or []).lower()
            if q in pname or q in cmdline:
                results.append({
                    "pid": info["pid"],
                    "name": info["name"],
                    "cpu": round(info.get("cpu_percent", 0) or 0, 1),
                    "mem_pct": round(info.get("memory_percent", 0) or 0, 1),
                    "cmdline": " ".join(info.get("cmdline") or [])[:120],
                })
        except Exception:
            continue
    return results


def kill_process(pid: int, force: bool = False) -> str:
    """Kill a process by PID."""
    try:
        import psutil
        p = psutil.Process(pid)
        name = p.name()
        if force:
            p.kill()
        else:
            p.terminate()
        return f"{'killed' if force else 'terminated'} {name} (PID {pid})"
    except Exception as e:
        return f"failed to kill PID {pid}: {e}"


# ── Network Intelligence ─────────────────────────────────────────

def get_network_connections() -> list[dict]:
    """Active network connections with process info."""
    try:
        import psutil
    except ImportError:
        return []

    conns = []
    for c in psutil.net_connections(kind="inet"):
        try:
            proc_name = ""
            if c.pid:
                try:
                    proc_name = psutil.Process(c.pid).name()
                except Exception:
                    pass
            if c.status == "LISTEN" or c.raddr:
                conns.append({
                    "proto": "tcp" if c.type == 1 else "udp",
                    "local": f"{c.laddr.ip}:{c.laddr.port}" if c.laddr else "",
                    "remote": f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else "",
                    "status": c.status,
                    "pid": c.pid,
                    "process": proc_name,
                })
        except Exception:
            continue
    return conns


def get_open_ports() -> list[dict]:
    """Listening ports."""
    out = _run("ss -tlnp 2>/dev/null")
    ports = []
    for line in out.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 4:
            local = parts[3]
            process = parts[-1] if "users:" in parts[-1] else ""
            # Extract process name from ss output
            m = re.search(r'"([^"]+)"', process)
            pname = m.group(1) if m else ""
            ports.append({"address": local, "process": pname})
    return ports


def get_bandwidth() -> dict:
    """Current network bandwidth usage."""
    try:
        import psutil
        counters = psutil.net_io_counters()
        return {
            "bytes_sent": counters.bytes_sent,
            "bytes_recv": counters.bytes_recv,
            "packets_sent": counters.packets_sent,
            "packets_recv": counters.packets_recv,
        }
    except Exception:
        return {}


def get_wifi_info() -> str:
    """Current WiFi connection info."""
    if shutil.which("nmcli"):
        return _run("nmcli -t -f active,ssid,signal,freq dev wifi 2>/dev/null | grep '^yes'")
    if shutil.which("iwconfig"):
        return _run("iwconfig 2>/dev/null | grep -E 'ESSID|Signal|Bit Rate'")
    return ""


# ── Hardware Intelligence ────────────────────────────────────────

def get_battery() -> dict:
    """Battery status."""
    try:
        import psutil
        bat = psutil.sensors_battery()
        if bat:
            return {
                "percent": round(bat.percent, 1),
                "plugged": bat.power_plugged,
                "seconds_left": bat.secsleft if bat.secsleft != -1 else None,
                "minutes_left": round(bat.secsleft / 60, 0) if bat.secsleft > 0 else None,
            }
    except Exception:
        pass
    return {}


def get_temperatures() -> dict:
    """CPU and hardware temperatures."""
    try:
        import psutil
        temps = psutil.sensors_temperatures()
        result = {}
        for name, entries in temps.items():
            for e in entries:
                label = e.label or name
                result[label] = {
                    "current": e.current,
                    "high": e.high,
                    "critical": e.critical,
                }
        return result
    except Exception:
        return {}


def get_gpu_info() -> dict:
    """GPU usage (NVIDIA or AMD)."""
    # NVIDIA
    if shutil.which("nvidia-smi"):
        out = _run("nvidia-smi --query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv,noheader,nounits 2>/dev/null")
        if out:
            parts = [p.strip() for p in out.split(",")]
            if len(parts) >= 5:
                return {
                    "name": parts[0],
                    "gpu_util": f"{parts[1]}%",
                    "mem_used": f"{parts[2]}MB",
                    "mem_total": f"{parts[3]}MB",
                    "temp": f"{parts[4]}C",
                    "vendor": "nvidia",
                }

    # AMD
    if Path("/sys/class/drm/card0/device/gpu_busy_percent").exists():
        gpu_pct = _run("cat /sys/class/drm/card0/device/gpu_busy_percent 2>/dev/null")
        return {"gpu_util": f"{gpu_pct}%", "vendor": "amd"}

    return {}


def get_usb_devices() -> list[str]:
    """Connected USB devices."""
    out = _run("lsusb 2>/dev/null")
    devices = []
    for line in out.splitlines():
        # Remove bus/device prefix, keep just the name
        m = re.search(r'ID \S+ (.+)', line)
        if m:
            devices.append(m.group(1).strip())
    return devices


def get_disk_info() -> list[dict]:
    """All mounted disks with usage."""
    try:
        import psutil
        disks = []
        for part in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(part.mountpoint)
                disks.append({
                    "device": part.device,
                    "mount": part.mountpoint,
                    "fstype": part.fstype,
                    "total_gb": round(usage.total / 1024**3, 1),
                    "used_gb": round(usage.used / 1024**3, 1),
                    "free_gb": round(usage.free / 1024**3, 1),
                    "percent": usage.percent,
                })
            except Exception:
                continue
        return disks
    except Exception:
        return []


def get_disk_io() -> dict:
    """Disk I/O counters."""
    try:
        import psutil
        io = psutil.disk_io_counters()
        if io:
            return {
                "read_mb": round(io.read_bytes / 1024**2, 1),
                "write_mb": round(io.write_bytes / 1024**2, 1),
                "read_count": io.read_count,
                "write_count": io.write_count,
            }
    except Exception:
        pass
    return {}


# ── Systemd / Services ───────────────────────────────────────────

def get_failed_services() -> list[str]:
    """List failed systemd services."""
    out = _run("systemctl --user list-units --state=failed --no-legend --no-pager 2>/dev/null")
    out += "\n" + _run("systemctl list-units --state=failed --no-legend --no-pager 2>/dev/null")
    services = []
    for line in out.splitlines():
        line = line.strip()
        if line:
            name = line.split()[0] if line.split() else ""
            if name and name not in services:
                services.append(name)
    return services


def get_service_status(name: str) -> str:
    """Get status of a specific service."""
    out = _run(f"systemctl status {name} --no-pager -l 2>/dev/null")
    if not out:
        out = _run(f"systemctl --user status {name} --no-pager -l 2>/dev/null")
    return out


def get_recent_boots() -> str:
    """Recent boot times."""
    return _run("journalctl --list-boots --no-pager 2>/dev/null | tail -5")


# ── Journal / Logs ───────────────────────────────────────────────

def get_recent_journal(n: int = 20, priority: str = "warning") -> list[str]:
    """Recent journal entries at given priority or higher."""
    # priority: emerg=0, alert=1, crit=2, err=3, warning=4, notice=5, info=6, debug=7
    prio_map = {"emergency": 0, "alert": 1, "critical": 2, "error": 3,
                "warning": 4, "notice": 5, "info": 6, "debug": 7}
    p = prio_map.get(priority, 4)
    out = _run(f"journalctl -p {p} --no-pager -n {n} --output=short 2>/dev/null")
    return [line for line in out.splitlines() if line.strip()]


def get_dmesg(n: int = 20) -> list[str]:
    """Recent kernel messages."""
    out = _run(f"dmesg --time-format iso 2>/dev/null | tail -{n}")
    if not out:
        out = _run(f"dmesg 2>/dev/null | tail -{n}")
    return [line for line in out.splitlines() if line.strip()]


def get_auth_log(n: int = 10) -> list[str]:
    """Recent auth/security log entries."""
    out = _run(f"journalctl -u sshd -n {n} --no-pager 2>/dev/null")
    if not out:
        out = _run(f"tail -{n} /var/log/auth.log 2>/dev/null")
    return [line for line in out.splitlines() if line.strip()]


# ── Kernel / System Info ─────────────────────────────────────────

def get_kernel_info() -> dict:
    """Kernel version and system info."""
    return {
        "kernel": _run("uname -r"),
        "arch": _run("uname -m"),
        "hostname": _run("hostname"),
        "distro": _run("lsb_release -ds 2>/dev/null") or _run("cat /etc/os-release 2>/dev/null | grep PRETTY_NAME | cut -d= -f2 | tr -d '\"'"),
        "uptime": _run("uptime -p 2>/dev/null"),
        "load_avg": _run("cat /proc/loadavg 2>/dev/null"),
    }


def get_users_logged_in() -> list[str]:
    """Currently logged-in users."""
    out = _run("who 2>/dev/null")
    return [line for line in out.splitlines() if line.strip()]


def get_environment_summary() -> dict:
    """Desktop environment and display info."""
    return {
        "desktop": os.environ.get("XDG_CURRENT_DESKTOP", ""),
        "session": os.environ.get("XDG_SESSION_TYPE", ""),
        "display": os.environ.get("DISPLAY", "") or os.environ.get("WAYLAND_DISPLAY", ""),
        "shell": os.environ.get("SHELL", ""),
        "user": os.environ.get("USER", ""),
        "home": os.environ.get("HOME", ""),
    }


# ── Package Management ───────────────────────────────────────────

def get_upgradable_packages() -> int:
    """Count of packages that need updating."""
    if shutil.which("apt"):
        out = _run("apt list --upgradable 2>/dev/null | grep -c upgradable")
        try:
            return int(out)
        except ValueError:
            return 0
    return 0


def get_recently_installed(n: int = 10) -> list[str]:
    """Recently installed packages."""
    if shutil.which("apt"):
        out = _run(f"grep ' install ' /var/log/dpkg.log 2>/dev/null | tail -{n}")
        return [line for line in out.splitlines() if line.strip()]
    return []


# ── Full System Snapshot ─────────────────────────────────────────

def full_system_snapshot() -> dict:
    """Complete system snapshot — everything Rokan needs to know."""
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        swap = psutil.swap_memory()
        boot = datetime.fromtimestamp(psutil.boot_time())
    except ImportError:
        return {"error": "psutil not installed"}

    return {
        "system": {
            **get_kernel_info(),
            "boot_time": boot.isoformat(),
            **get_environment_summary(),
        },
        "cpu": {
            "percent": cpu,
            "cores_physical": psutil.cpu_count(logical=False),
            "cores_logical": psutil.cpu_count(logical=True),
            "freq_mhz": round(psutil.cpu_freq().current, 0) if psutil.cpu_freq() else 0,
            "load_1m": os.getloadavg()[0] if hasattr(os, "getloadavg") else 0,
            "load_5m": os.getloadavg()[1] if hasattr(os, "getloadavg") else 0,
        },
        "memory": {
            "total_gb": round(mem.total / 1024**3, 1),
            "used_gb": round(mem.used / 1024**3, 1),
            "available_gb": round(mem.available / 1024**3, 1),
            "percent": mem.percent,
            "swap_percent": swap.percent,
            "swap_used_gb": round(swap.used / 1024**3, 1),
        },
        "disk": {
            "percent": disk.percent,
            "free_gb": round(disk.free / 1024**3, 1),
            "all_mounts": get_disk_info(),
            "io": get_disk_io(),
        },
        "battery": get_battery(),
        "temperatures": get_temperatures(),
        "gpu": get_gpu_info(),
        "network": {
            "bandwidth": get_bandwidth(),
            "wifi": get_wifi_info(),
            "connections": len(get_network_connections()),
            "open_ports": len(get_open_ports()),
        },
        "processes": {
            "total": len(psutil.pids()),
            "top_cpu": get_top_processes(5, "cpu"),
            "top_memory": get_top_processes(5, "memory"),
        },
        "services": {
            "failed": get_failed_services(),
        },
        "usb_devices": get_usb_devices(),
        "packages_upgradable": get_upgradable_packages(),
    }


def build_context_string() -> str:
    """Build a compact context string for LLM injection from full snapshot."""
    try:
        snap = full_system_snapshot()
    except Exception:
        return ""

    parts = []

    # System
    s = snap.get("system", {})
    parts.append(f"[SYSTEM] {s.get('distro','')} | kernel {s.get('kernel','')} | {s.get('uptime','')}")

    # CPU
    c = snap.get("cpu", {})
    parts.append(f"[CPU] {c.get('percent',0)}% | {c.get('cores_logical',0)} cores | load {c.get('load_1m',0):.1f}")

    # Memory
    m = snap.get("memory", {})
    parts.append(f"[RAM] {m.get('percent',0)}% | {m.get('used_gb',0)}GB/{m.get('total_gb',0)}GB | swap {m.get('swap_percent',0)}%")

    # Disk
    d = snap.get("disk", {})
    parts.append(f"[DISK] {d.get('percent',0)}% | {d.get('free_gb',0)}GB free")

    # Battery
    bat = snap.get("battery", {})
    if bat:
        plug = "plugged" if bat.get("plugged") else "on battery"
        mins = bat.get("minutes_left")
        t = f" ({int(mins)}min left)" if mins else ""
        parts.append(f"[BATTERY] {bat.get('percent',0)}% {plug}{t}")

    # Temperature
    temps = snap.get("temperatures", {})
    if temps:
        hottest = max(temps.values(), key=lambda x: x.get("current", 0), default={})
        if hottest:
            parts.append(f"[TEMP] {hottest.get('current',0)}C")

    # GPU
    gpu = snap.get("gpu", {})
    if gpu:
        parts.append(f"[GPU] {gpu.get('name',gpu.get('vendor',''))} {gpu.get('gpu_util','')} | {gpu.get('mem_used','')}/{gpu.get('mem_total','')}")

    # Network
    net = snap.get("network", {})
    parts.append(f"[NET] {net.get('connections',0)} connections | {net.get('open_ports',0)} listening ports")
    if net.get("wifi"):
        parts.append(f"[WIFI] {net['wifi']}")

    # Processes
    procs = snap.get("processes", {})
    parts.append(f"[PROCS] {procs.get('total',0)} total")
    top_cpu = procs.get("top_cpu", [])
    if top_cpu and top_cpu[0].get("cpu", 0) > 5:
        top = top_cpu[0]
        parts.append(f"[TOP CPU] {top['name']} PID={top['pid']} {top['cpu']}%")
    top_mem = procs.get("top_memory", [])
    if top_mem:
        top = top_mem[0]
        parts.append(f"[TOP MEM] {top['name']} PID={top['pid']} {top['mem_mb']}MB ({top['mem_pct']}%)")

    # Failed services
    failed = snap.get("services", {}).get("failed", [])
    if failed:
        parts.append(f"[FAILED SERVICES] {', '.join(failed[:5])}")

    # USB
    usb = snap.get("usb_devices", [])
    if usb:
        parts.append(f"[USB] {len(usb)} devices: {', '.join(usb[:3])}")

    # Updates
    upgradable = snap.get("packages_upgradable", 0)
    if upgradable:
        parts.append(f"[UPDATES] {upgradable} packages need updating")

    return "\n".join(parts)
