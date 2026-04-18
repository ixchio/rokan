# rokan-system

**Rokan's System Agent** — Linux-native monitoring and control. CPU, RAM, disk, processes, services — all at your command.

## Description

Deep Linux system integration for monitoring, diagnostics, and control. Rokan watches your system like a shadow monarch watches his domain — aware of everything, intervening when necessary.

## Capabilities

| Feature | Command | Description |
|---------|---------|-------------|
| **System Stats** | `status` | CPU, RAM, disk, load |
| **Process Monitor** | `processes` | Top processes, resource hogs |
| **Service Control** | `service <name>` | Start/stop/restart services |
| **Disk Usage** | `disk` | Storage analysis, cleanup |
| **Network** | `network` | Connections, bandwidth |
| **Logs** | `logs <service>` | Tail and analyze logs |
| **Alerts** | Auto | Proactive warnings |

## When to Use

- "What's my system status?"
- "Why is my CPU at 100%?"
- "Show me memory hogs"
- "Restart nginx service"
- "Clean up disk space"
- "Check failed services"

## Setup

```bash
# 1. Install dependencies
pip install psutil pydbus dbus-python

# 2. Grant necessary permissions (optional)
# For service control without sudo:
sudo usermod -aG systemd-journal $USER

# 3. For network monitoring
sudo setcap cap_net_raw+ep $(which python3)
```

## Configuration

Add to `~/.openclaw/config.yaml`:

```yaml
skills:
  rokan-system:
    enabled: true
    check_interval_seconds: 30
    
    thresholds:
      cpu_percent: 80
      memory_percent: 85
      disk_percent: 90
      load_average: 4.0
      zombie_processes: 10
    
    proactive_alerts:
      high_cpu: true
      high_memory: true
      disk_full: true
      long_processes: true
      failed_services: true
    
    long_process_threshold_minutes: 60
    
    services_to_monitor:
      - ssh
      - docker
      - nginx
      - postgresql
      - redis
    
    actions:
      can_kill_processes: false  # Requires confirmation
      can_restart_services: false
      can_clean_temp: true
      can_update_packages: false
    
    notifications:
      desktop: true
      log_to_file: true
```

## Usage

### System Overview
```
User: "System status"
[Rokan]: 
┌─ System Status ─────────────────┐
│ CPU: 23% (8 cores)              │
│ RAM: 12.4GB / 32GB (39%)        │
│ Disk: 234GB / 1TB (23%)         │
│ Load: 0.45 0.52 0.48            │
│ Uptime: 14 days, 3 hours        │
│ Processes: 342 running          │
└─────────────────────────────────┘
```

### Process Analysis
```
User: "What's using my CPU?"
[Rokan]: "Top CPU consumers:
  1. python3 (training.py) - 45% CPU, 2.1GB RAM
  2. chrome - 12% CPU, 1.8GB RAM
  3. dockerd - 8% CPU, 512MB RAM

Note: python3 training.py has been running for 3 hours."
```

### Service Management
```
User: "Restart docker"
[Rokan]: "Restarting docker service... ✓ Done"
```

### Disk Cleanup
```
User: "Clean up disk"
[Rokan]: "Found 2.3GB to clean:
  - /tmp: 456MB
  - Docker unused images: 1.2GB
  - Old logs: 678MB

Clean these? (y/n)"
```

### Proactive Alerts
```
[Rokan]: ⚠️ Alert: Build process (make) running for 45 minutes.
         CPU: 98% | Memory: 4.2GB
         Check if stuck? (y/n/details)"
```

## API

### `system.get_status()`
Get complete system status snapshot.

### `system.get_processes(sort_by="cpu", limit=10)`
Get top processes by resource usage.

### `system.get_services()`
List all services and their status.

### `system.service_action(name, action)`
Control a service (start/stop/restart/status).

### `system.get_disk_usage()`
Get disk usage by filesystem and directory.

### `system.clean_temp()`
Clean temporary files and caches.

### `system.get_network_connections()`
Get active network connections.

### `system.kill_process(pid, signal=15)`
Send signal to process (requires confirmation).

## Proactive Monitoring

Rokan automatically watches for:

1. **High Resource Usage** — CPU >80% for >5 min
2. **Memory Pressure** — RAM >85%
3. **Disk Full** — Any partition >90%
4. **Long Processes** — Running >1 hour with high CPU
5. **Failed Services** — systemd services in failed state
6. **Zombie Processes** — >10 zombie processes
7. **Load Spikes** — Load avg >CPU count

## Files

- `system_agent.py` — Main system interface
- `monitor.py` — Resource monitoring
- `process_manager.py` — Process control
- `service_manager.py` — systemd integration
- `disk_analyzer.py` — Storage analysis
- `network_monitor.py` — Network stats
- `alerts.py` — Alert system

## License

MIT — Part of Rokan Skill Pack for OpenClaw
