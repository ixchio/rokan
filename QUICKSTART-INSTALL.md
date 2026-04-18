# Rokan Quick Start Guide

## The 30-Second Installation

```bash
cd rokan-skills
./install-rokan.sh
rokan
```

That's it! The installer handles everything:
- ✓ Python virtual environment
- ✓ All dependencies
- ✓ CLI launcher
- ✓ Desktop shortcut
- ✓ Systemd integration
- ✓ Data directories

## Available Now

### Command Line
```bash
rokan ask "What is machine learning?"
rokan ask --think "Solve this algorithm problem..."
rokan ask --code "Generate a Python function"
rokan ask --fast "Quick summary of docker"
```

### Terminal UI
```bash
rokan    # Beautiful full-screen interface
```

### System Info
```bash
rokan status    # Overall status
rokan models    # Show AI model stack
rokan system    # Live system metrics
```

## Inside the TUI

Once running, you can:
- Type questions directly
- Press Ctrl+Q to quit
- Use `/think`, `/code`, `/fast` prefix for models
- Toggle `/voice` output
- Clear chat with `/clear`
- View CPU/RAM/Disk in sidebar

## Installation Modes

### User (Default - Recommended)
```bash
./install-rokan.sh user
# or just:
./install-rokan.sh
```
- No sudo needed
- Install location: `~/.local/bin/rokan`
- Data: `~/.rokan/`

### System-Wide
```bash
sudo ./install-rokan.sh system
```
- Requires sudo
- Install location: `/usr/local/bin/rokan`
- Available to all users

## First Run Setup

1. **Check it works:**
   ```bash
   rokan status
   ```

2. **Get API key (optional but recommended):**
   - Visit: https://build.nvidia.com
   - Get free NVIDIA API key

3. **Set it:**
   ```bash
   export NVIDIA_API_KEY="nvapi-..."
   ```

4. **Launch TUI:**
   ```bash
   rokan
   ```

5. **Ask something:**
   ```
   ▸ What are the latest Linux kernel features?
   ```

## Models Available

| Command | Model | Speed | Best For |
|---------|-------|-------|----------|
| `rokan ask "..."` | Llama 70B | Balanced | General questions |
| `rokan ask --think "..."` | GLM 4.7 | Slow | Deep reasoning |
| `rokan ask --fast "..."` | Step 3.5 | Fast | Quick answers |
| `rokan ask --code "..."` | QwQ 32B | Slow | Code generation |

## Enable Auto-Start (Optional)

```bash
systemctl --user enable rokan
systemctl --user start rokan

# Now rokan runs at login
# CLI commands still work: rokan ask "..."
```

## Uninstall

```bash
./uninstall-rokan.sh
# Choose to keep or delete data
```

## Troubleshooting

**Command not found?**
```bash
export PATH="$HOME/.local/bin:$PATH"
# Add to ~/.bashrc
```

**Python error?**
```bash
pip install -r requirements.txt
```

**API key issue?**
```bash
export NVIDIA_API_KEY="your-key-here"
rokan ask "test"
```

## File Location Reference

| What | User Mode | System Mode |
|------|-----------|-------------|
| Program | `~/.local/bin/rokan` | `/usr/local/bin/rokan` |
| Python Env | `~/.local/opt/rokan/venv` | `/opt/rokan/venv` |
| Service | `~/.config/systemd/user/rokan.service` | `/etc/systemd/system/rokan.service` |
| Data | `~/.rokan/` | `~/.rokan/` (same) |
| Config | `~/.config/rokan/` | `~/.config/rokan/` (same) |

## Useful Commands

```bash
# See all options
rokan --help

# Check system status
rokan status

# Show configuration
rokan config

# System metrics
rokan system

# Show available models
rokan models

# Run setup wizard
rokan setup

# Manage service (user mode)
systemctl --user status rokan
systemctl --user start rokan
systemctl --user stop rokan
journalctl --user -u rokan -f    # View logs
```

## Next Steps

1. ✓ Install and test with `rokan status`
2. ✓ Set your NVIDIA API key
3. ✓ Try the TUI: `rokan`
4. ✓ Test CLI: `rokan ask "test"`
5. ✓ Explore models: `rokan models`

**You're ready to go!**

For detailed information, see:
- [INSTALL.md](INSTALL.md) - Full installation guide
- [README-LINUX-SOFTWARE.md](README-LINUX-SOFTWARE.md) - Complete features
- setup.py - Package details

---

*Rokan is ready. Execute.*
