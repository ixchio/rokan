"""
Rokan System Agent
Linux-native system monitoring and control
"""

import os
import re
import json
import subprocess
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

# Optional imports
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


try:
    import dbus
    HAS_DBUS = True
except ImportError:
    HAS_DBUS = False


@dataclass
class SystemStatus:
    """System status snapshot"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    memory_total_gb: float
    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float
    load_average: tuple
    uptime_seconds: float
    process_count: int
    boot_time: datetime


@dataclass
class ProcessInfo:
    """Process information"""
    pid: int
    name: str
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    status: str
    created: datetime
    username: str
    cmdline: str


class SystemAgent:
    """
    Linux system monitoring and control agent
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.thresholds = self.config.get("thresholds", {})
        self.alerts_enabled = self.config.get("proactive_alerts", {})
        self.monitoring = False
        self.alert_history = []
    
    def get_status(self) -> SystemStatus:
        """Get complete system status"""
        if not HAS_PSUTIL:
            return self._fallback_status()
        
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory
        memory = psutil.virtual_memory()
        memory_used_gb = memory.used / (1024**3)
        memory_total_gb = memory.total / (1024**3)
        
        # Disk
        disk = psutil.disk_usage('/')
        disk_used_gb = disk.used / (1024**3)
        disk_total_gb = disk.total / (1024**3)
        
        # Load average
        load_avg = os.getloadavg()
        
        # Uptime
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime_seconds = (datetime.now() - boot_time).total_seconds()
        
        # Process count
        process_count = len(psutil.pids())
        
        return SystemStatus(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_used_gb=memory_used_gb,
            memory_total_gb=memory_total_gb,
            disk_percent=disk.percent,
            disk_used_gb=disk_used_gb,
            disk_total_gb=disk_total_gb,
            load_average=load_avg,
            uptime_seconds=uptime_seconds,
            process_count=process_count,
            boot_time=boot_time
        )
    
    def _fallback_status(self) -> SystemStatus:
        """Fallback status without psutil"""
        # Basic info from /proc
        try:
            with open('/proc/loadavg') as f:
                load_parts = f.read().split()
                load_avg = (float(load_parts[0]), float(load_parts[1]), float(load_parts[2]))
        except:
            load_avg = (0.0, 0.0, 0.0)
        
        try:
            with open('/proc/uptime') as f:
                uptime_seconds = float(f.read().split()[0])
        except:
            uptime_seconds = 0.0
        
        return SystemStatus(
            timestamp=datetime.now(),
            cpu_percent=0.0,
            memory_percent=0.0,
            memory_used_gb=0.0,
            memory_total_gb=0.0,
            disk_percent=0.0,
            disk_used_gb=0.0,
            disk_total_gb=0.0,
            load_average=load_avg,
            uptime_seconds=uptime_seconds,
            process_count=0,
            boot_time=datetime.now()
        )
    
    def get_processes(self, 
                      sort_by: str = "cpu", 
                      limit: int = 10) -> List[ProcessInfo]:
        """Get top processes by resource usage"""
        if not HAS_PSUTIL:
            return []
        
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 
                                          'memory_percent', 'memory_info',
                                          'status', 'create_time', 'username', 'cmdline']):
            try:
                info = proc.info
                processes.append(ProcessInfo(
                    pid=info['pid'],
                    name=info['name'] or "unknown",
                    cpu_percent=info['cpu_percent'] or 0.0,
                    memory_percent=info['memory_percent'] or 0.0,
                    memory_mb=(info['memory_info'].rss / (1024**2)) if info['memory_info'] else 0.0,
                    status=info['status'] or "unknown",
                    created=datetime.fromtimestamp(info['create_time']) if info['create_time'] else datetime.now(),
                    username=info['username'] or "unknown",
                    cmdline=' '.join(info['cmdline']) if info['cmdline'] else ""
                ))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # Sort
        if sort_by == "cpu":
            processes.sort(key=lambda p: p.cpu_percent, reverse=True)
        elif sort_by == "memory":
            processes.sort(key=lambda p: p.memory_percent, reverse=True)
        
        return processes[:limit]
    
    def get_services(self) -> List[Dict]:
        """Get systemd services status"""
        services = []
        
        try:
            result = subprocess.run(
                ['systemctl', 'list-units', '--type=service', '--state=running', '--no-pager', '-q'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            for line in result.stdout.split('\n')[1:]:
                parts = line.split()
                if len(parts) >= 4:
                    services.append({
                        "name": parts[0],
                        "load": parts[1],
                        "active": parts[2],
                        "sub": parts[3],
                        "description": ' '.join(parts[4:]) if len(parts) > 4 else ""
                    })
        except Exception as e:
            print(f"Service check error: {e}")
        
        return services
    
    def get_disk_usage(self) -> List[Dict]:
        """Get disk usage by filesystem"""
        if not HAS_PSUTIL:
            return []
        
        disks = []
        for part in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(part.mountpoint)
                disks.append({
                    "device": part.device,
                    "mountpoint": part.mountpoint,
                    "fstype": part.fstype,
                    "total_gb": usage.total / (1024**3),
                    "used_gb": usage.used / (1024**3),
                    "free_gb": usage.free / (1024**3),
                    "percent": usage.percent
                })
            except PermissionError:
                pass
        
        return disks
    
    def get_network_connections(self) -> Dict:
        """Get network connection info"""
        if not HAS_PSUTIL:
            return {}
        
        try:
            connections = psutil.net_connections()
            
            by_status = {}
            for conn in connections:
                status = conn.status
                by_status[status] = by_status.get(status, 0) + 1
            
            io_counters = psutil.net_io_counters()
            
            return {
                "connections_by_status": by_status,
                "total_connections": len(connections),
                "bytes_sent": io_counters.bytes_sent,
                "bytes_recv": io_counters.bytes_recv,
                "packets_sent": io_counters.packets_sent,
                "packets_recv": io_counters.packets_recv
            }
        except Exception as e:
            return {"error": str(e)}
    
    def check_alerts(self) -> List[Dict]:
        """Check for alert conditions"""
        alerts = []
        status = self.get_status()
        
        # CPU alert
        if self.alerts_enabled.get("high_cpu"):
            threshold = self.thresholds.get("cpu_percent", 80)
            if status.cpu_percent > threshold:
                alerts.append({
                    "type": "high_cpu",
                    "severity": "warning",
                    "message": f"CPU usage at {status.cpu_percent:.1f}% (threshold: {threshold}%)",
                    "timestamp": datetime.now()
                })
        
        # Memory alert
        if self.alerts_enabled.get("high_memory"):
            threshold = self.thresholds.get("memory_percent", 85)
            if status.memory_percent > threshold:
                alerts.append({
                    "type": "high_memory",
                    "severity": "warning",
                    "message": f"Memory usage at {status.memory_percent:.1f}% (threshold: {threshold}%)",
                    "timestamp": datetime.now()
                })
        
        # Disk alert
        if self.alerts_enabled.get("disk_full"):
            threshold = self.thresholds.get("disk_percent", 90)
            if status.disk_percent > threshold:
                alerts.append({
                    "type": "disk_full",
                    "severity": "critical",
                    "message": f"Disk usage at {status.disk_percent:.1f}% (threshold: {threshold}%)",
                    "timestamp": datetime.now()
                })
        
        # Long processes
        if self.alerts_enabled.get("long_processes"):
            threshold_minutes = self.config.get("long_process_threshold_minutes", 60)
            processes = self.get_processes(sort_by="cpu", limit=20)
            
            for proc in processes:
                runtime = (datetime.now() - proc.created).total_seconds() / 60
                if runtime > threshold_minutes and proc.cpu_percent > 50:
                    alerts.append({
                        "type": "long_process",
                        "severity": "info",
                        "message": f"Process '{proc.name}' (PID {proc.pid}) running for {runtime:.0f} minutes at {proc.cpu_percent:.1f}% CPU",
                        "timestamp": datetime.now(),
                        "process": proc
                    })
        
        self.alert_history.extend(alerts)
        return alerts
    
    def format_status(self, status: SystemStatus = None) -> str:
        """Format system status for display"""
        if status is None:
            status = self.get_status()
        
        uptime_days = status.uptime_seconds / 86400
        
        output = []
        output.append("┌─ System Status ─────────────────────────┐")
        output.append(f"│ CPU: {status.cpu_percent:5.1f}% (Load: {status.load_average[0]:.2f})        │")
        output.append(f"│ RAM: {status.memory_used_gb:5.1f}/{status.memory_total_gb:.1f}GB ({status.memory_percent:.0f}%)          │")
        output.append(f"│ Disk: {status.disk_used_gb:5.1f}/{status.disk_total_gb:.1f}GB ({status.disk_percent:.0f}%)         │")
        output.append(f"│ Uptime: {uptime_days:.1f} days                    │")
        output.append(f"│ Processes: {status.process_count}                      │")
        output.append("└─────────────────────────────────────────┘")
        
        return "\n".join(output)
    
    def format_processes(self, processes: List[ProcessInfo] = None) -> str:
        """Format process list for display"""
        if processes is None:
            processes = self.get_processes()
        
        output = []
        output.append("┌─ Top Processes ─────────────────────────────────────────┐")
        output.append(f"│ {'PID':>6} {'Name':<20} {'CPU%':>6} {'Mem%':>6} {'Mem(MB)':>8} │")
        output.append("├─────────────────────────────────────────────────────────┤")
        
        for proc in processes[:10]:
            name = proc.name[:18] + ".." if len(proc.name) > 20 else proc.name
            output.append(f"│ {proc.pid:>6} {name:<20} {proc.cpu_percent:>6.1f} {proc.memory_percent:>6.1f} {proc.memory_mb:>8.1f} │")
        
        output.append("└─────────────────────────────────────────────────────────┘")
        
        return "\n".join(output)


# OpenClaw skill interface
class RokanSystemSkill:
    """OpenClaw skill interface for rokan-system"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.agent = SystemAgent(config)
    
    def status(self) -> str:
        """Get system status"""
        return self.agent.format_status()
    
    def processes(self, sort: str = "cpu", limit: int = 10) -> str:
        """Get top processes"""
        procs = self.agent.get_processes(sort_by=sort, limit=limit)
        return self.agent.format_processes(procs)
    
    def disk(self) -> str:
        """Get disk usage"""
        disks = self.agent.get_disk_usage()
        
        output = ["Disk Usage:"]
        for d in disks:
            output.append(f"  {d['device']} ({d['mountpoint']}): {d['used_gb']:.1f}/{d['total_gb']:.1f}GB ({d['percent']}%)")
        
        return "\n".join(output)
    
    def services(self) -> str:
        """Get running services"""
        svcs = self.agent.get_services()
        
        output = ["Running Services:"]
        for s in svcs[:20]:
            output.append(f"  {s['name']} - {s['sub']}")
        
        return "\n".join(output)
    
    def alerts(self) -> str:
        """Check for alerts"""
        alerts = self.agent.check_alerts()
        
        if not alerts:
            return "No alerts. System is healthy."
        
        output = ["System Alerts:"]
        for alert in alerts:
            icon = "⚠️" if alert["severity"] == "warning" else "🔴" if alert["severity"] == "critical" else "ℹ️"
            output.append(f"{icon} {alert['message']}")
        
        return "\n".join(output)


# Export for OpenClaw
skill = RokanSystemSkill
