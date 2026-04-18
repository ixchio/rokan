# rokan-code

**Rokan's Code Executor** — Sandboxed Python execution with safety controls. Write, test, and run code securely.

## Description

Execute Python code in a restricted environment with resource limits and security policies. Perfect for quick scripts, automation, and testing without risking your system.

## Safety Features

| Feature | Implementation | Protection |
|---------|---------------|------------|
| **Import Whitelist** | AST analysis | Only allowed modules |
| **No Network** | Socket blocking | Can't exfiltrate data |
| **No Root** | User namespace | Can't modify system |
| **Memory Limit** | Resource limits | Max 512MB per execution |
| **Timeout** | Signal alarm | Max 30 seconds |
| **File Restrictions** | Path sandbox | Read-only or temp only |

## When to Use

- "Write a script to rename these files"
- "Test this Python function"
- "Calculate this for me"
- "Parse this JSON"
- "Convert this data format"

## Setup

```bash
# 1. Install dependencies
pip install restrictedpython docker

# 2. Optional: Docker sandbox (recommended)
# Rokan will auto-create a restricted container
docker pull python:3.11-slim

# 3. Create sandbox directory
mkdir -p ~/.rokan/sandbox
chmod 700 ~/.rokan/sandbox
```

## Configuration

Add to `~/.openclaw/config.yaml`:

```yaml
skills:
  rokan-code:
    enabled: true
    
    sandbox:
      type: "subprocess"  # or "docker"
      timeout_seconds: 30
      max_memory_mb: 512
      max_output_lines: 100
      
    allowed_imports:
      - os
      - sys
      - json
      - re
      - datetime
      - math
      - random
      - collections
      - itertools
      - functools
      - typing
      - pathlib
      - hashlib
      - base64
      - urllib.parse
      - http.client
      - statistics
      - decimal
      - fractions
      - string
      - time
      - uuid
      - csv
      - io
      - pprint
      - html
      - xml.etree.ElementTree
      
    blocked_imports:
      - subprocess
      - socket
      - ctypes
      - mmap
      - multiprocessing
      - threading
      - asyncio
      - tkinter
      - sqlite3  # Use memory-only
      
    file_system:
      access: "temp-only"  # none, temp-only, read-only
      temp_dir: "~/.rokan/sandbox/temp"
      allowed_paths: []
      
    network:
      enabled: false
      allowed_hosts: []
      
    docker:
      image: "python:3.11-slim"
      memory_limit: "512m"
      cpu_limit: "1.0"
      network_mode: "none"
```

## Usage

### Simple Calculation
```
User: "Calculate fibonacci(100)"
[Rokan]: 
```python
# Executing in sandbox...
def fibonacci(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a

result = fibonacci(100)
print(result)
```
Result: 354224848179261915075
```

### File Processing
```
User: "List all Python files in ~/projects and count lines"
[Rokan]: 
```python
from pathlib import Path
import os

projects = Path.home() / "projects"
py_files = list(projects.rglob("*.py"))

results = []
for f in py_files[:50]:  # Limit to 50 files
    try:
        lines = len(f.read_text().splitlines())
        results.append((f.name, lines))
    except:
        pass

total_lines = sum(r[1] for r in results)
print(f"Found {len(results)} Python files, {total_lines} total lines")
for name, lines in sorted(results, key=lambda x: -x[1])[:10]:
    print(f"  {name}: {lines} lines")
```
```

### Data Processing
```
User: "Parse this JSON and extract names"
[Rokan]: 
```python
import json

data = '''{"users": [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]}'''
parsed = json.loads(data)
names = [u["name"] for u in parsed["users"]]
print(f"Names: {', '.join(names)}")
```
```

## API

### `code.execute(python_code, context={})`
Execute Python code in sandbox.

Returns:
```python
{
  "success": True,
  "output": "printed output",
  "result": <last expression value>,
  "execution_time": 0.45,
  "memory_used": "24MB"
}
```

### `code.validate(code)`
Check if code passes security validation.

### `code.install_package(package_name)`
Install a package in the sandbox (if allowed).

### `code.create_script(name, code)`
Save code as reusable script in `~/.rokan/scripts/`.

### `code.run_script(name, args=[])`
Execute a saved script.

## Security Model

1. **Static Analysis** — AST parsing blocks dangerous imports
2. **Runtime Restrictions** — Resource limits prevent DoS
3. **Filesystem Isolation** — Temp-only or read-only access
4. **Network Blocking** — No outbound connections
5. **Docker Option** — Full container isolation available

## Example: Safe vs Blocked

### ✅ Safe Code
```python
import json, math, datetime
from pathlib import Path

# File reading (if allowed)
data = Path("/tmp/test.txt").read_text()

# Calculations
result = math.sqrt(sum(range(100)))

# Data processing
parsed = json.loads(data)
```

### ❌ Blocked Code
```python
import subprocess  # Blocked import
subprocess.run(["rm", "-rf", "/"])  # Would be blocked

import socket  # Blocked import
sock = socket.socket()  # Network access denied

# File system escape
open("/etc/passwd", "w").write("hacked")  # Read-only FS
```

## Files

- `code_executor.py` — Main execution engine
- `sandbox.py` — Subprocess sandbox
- `docker_sandbox.py` — Docker-based isolation
- `validator.py` — Code security validator
- `stdlib.py` — Safe standard library wrapper

## License

MIT — Part of Rokan Skill Pack for OpenClaw
