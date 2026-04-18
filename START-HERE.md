# 🚀 START HERE - Rokan Linux Software Installation

## What You Now Have

Rokan is now **a complete Linux software program** ready to install on any Linux system.

### ✅ What's Included

1. **Professional Installation Scripts**
   - `install-rokan.sh` - Automated installer (user or system-wide)
   - `uninstall-rokan.sh` - Safe uninstallation

2. **Complete Documentation**
   - QUICKSTART-INSTALL.md (5-min quick start)
   - INSTALL.md (comprehensive guide)  
   - README-LINUX-SOFTWARE.md (features overview)
   - INSTALLATION-SUMMARY.txt (reference)

3. **Updated Application**
   - CLI updated with latest models
   - Beautiful TUI with system monitoring
   - 4 AI models to choose from
   - Desktop integration ready

---

## The 3-Step Installation

### Step 1: Navigate
```bash
cd "/home/ruzvad/Music/OpenClaw to Rokan/rokan-skills"
```

### Step 2: Install
```bash
chmod +x install-rokan.sh
./install-rokan.sh
```

### Step 3: Use
```bash
rokan              # Launch TUI (beautiful interface)
rokan ask "test"   # Test CLI command
```

**That's it!** The installer handles everything automatically.

---

## What Gets Installed

### Available Commands
```bash
rokan                              # Main TUI interface
rokan ask "question"               # Ask AI anything
rokan ask --think "complex"        # Deep reasoning model
rokan ask --code "code task"       # Code generation model
rokan ask --fast "summary"         # Quick response
rokan status                       # System status
rokan models                       # Show model info
rokan system                       # Live metrics
rokan config                       # Configuration
rokan setup                        # Setup wizard
```

### System Integration
✓ Desktop launcher (app menu)
✓ systemd service (optional auto-start)
✓ CLI command available everywhere
✓ Professional Linux standards

### AI Models
| Model | Use Case | Speed |
|-------|----------|-------|
| Llama 3.3 70B | General queries | Balanced |
| GLM 4.7 | Deep reasoning | Slow |
| Step 3.5 Flash | Quick answers | Fast |
| QwQ 32B | Code work | Slow |

---

## Two Installation Modes

### 👤 User Mode (Recommended)
```bash
./install-rokan.sh
```
- No `sudo` needed
- Install for current user only
- Binary: `~/.local/bin/rokan`
- Good for: Personal use, development

### 💼 System Mode
```bash
sudo ./install-rokan.sh system
```
- Requires `sudo`
- Install for all users
- Binary: `/usr/local/bin/rokan`
- Good for: Shared systems, production

---

## Essential Commands After Installation

### Verify Installation
```bash
rokan status    # Shows version, API status, system info
rokan models    # Shows all available models
```

### Launch
```bash
rokan           # Beautiful terminal UI
rokan ask "Hi"  # Quick CLI test
```

### Optional: Enable Auto-Start
```bash
systemctl --user enable rokan     # Auto-start on login
systemctl --user start rokan      # Start now
```

### View Logs
```bash
journalctl --user -u rokan -f     # Real-time logs
```

---

## Troubleshooting

### "Command Not Found"
```bash
export PATH="$HOME/.local/bin:$PATH"
# Add to ~/.bashrc for permanent fix
```

### Python Error
```bash
python3 --version  # Check it's 3.10+
pip install -r requirements.txt  # Reinstall deps
```

### API Key Issue
```bash
export NVIDIA_API_KEY="nvapi-..."  # Set your key
# Get free key at: https://build.nvidia.com
```

See **INSTALL.md** for comprehensive troubleshooting.

---

## Directory Structure

```
After Installation:

User Mode:
  ~/.local/bin/rokan              ← Command to run
  ~/.local/opt/rokan/venv         ← Python environment
  ~/.config/systemd/user/...      ← Auto-start config
  ~/.local/share/applications/... ← Desktop launcher

Shared (both modes):
  ~/.rokan/logs                   ← Application logs
  ~/.rokan/cache                  ← Cache files
  ~/.rokan/data                   ← Application data
  ~/.config/rokan/                ← Configuration
```

---

## Which Documentation to Read?

### 5 Minutes - Ultra Quick Start
→ **QUICKSTART-INSTALL.md**
- Basic installation steps
- Essential commands
- Troubleshooting checklist

### 15 Minutes - Get Everything
→ **INSTALL.md** 
- Complete installation guide
- Configuration options
- Advanced usage
- Service management
- Full troubleshooting

### 10 Minutes - Understand Rokan
→ **README-LINUX-SOFTWARE.md**
- Features overview
- What each component does
- File manifest
- System integration details

### Reference
→ **INSTALLATION-SUMMARY.txt**
- Quick reference guide
- Checklist format
- Installation overview

---

## Quick Reference Commands

| Task | Command |
|------|---------|
| Install | `./install-rokan.sh` |
| Launch TUI | `rokan` |
| Ask anything | `rokan ask "question"` |
| Status check | `rokan status` |
| Show models | `rokan models` |
| System metrics | `rokan system` |
| Enable auto-start | `systemctl --user enable rokan` |
| View logs | `journalctl --user -u rokan -f` |
| Uninstall | `./uninstall-rokan.sh` |

---

## System Requirements Checklist

Before installing, verify:
- [ ] Python 3.10 or newer
- [ ] pip package manager
- [ ] ~500MB disk space  
- [ ] 2GB RAM (4GB+ recommended)
- [ ] Linux operating system

Check Python:
```bash
python3 --version  # Should show 3.10+
```

---

## First Run Walkthrough

```bash
# 1. Install
cd "/home/ruzvad/Music/OpenClaw to Rokan/rokan-skills"
chmod +x install-rokan.sh
./install-rokan.sh
# ... installer runs automatically ...

# 2. Verify
rokan status
# Shows: Version 2.0.0, system info, model stack

# 3. Set API key (optional but recommended)
export NVIDIA_API_KEY="nvapi-..."
# Get free key at: https://build.nvidia.com

# 4. Try it out
rokan ask "What is machine learning?"
# Response streams to terminal

# 5. Launch full TUI
rokan
# Beautiful terminal interface opens
```

---

## Features You'll Have

✓ **Beautiful Terminal UI** - Full-screen interface with system monitoring
✓ **CLI Access** - Use `rokan ask` from anywhere
✓ **Multiple Models** - Choose the right AI for your task
✓ **Desktop Launcher** - Click to launch from app menu
✓ **Auto-Start** - Optional systemd service
✓ **System Monitoring** - Real-time CPU/RAM/Disk
✓ **Linux Native** - Uses systemd, standard locations
✓ **Professional** - Production-ready software

---

## Support & Help

### Get Help
```bash
rokan --help           # Show all commands
rokan ask --help       # Show ask command options
rokan setup            # Run setup wizard
rokan config           # Show configuration paths
```

### Check Installation
```bash
rokan status           # Overall status report
python3 --version     # Verify Python
pip3 list | grep -E "textual|openai|psutil"  # Check deps
```

### View Logs
```bash
journalctl --user -u rokan -f    # Real-time logs
tail -f ~/.rokan/logs/*          # Application logs
```

---

## Next Steps

1. ✅ You have the installer ready
2. 👉 Run: `cd rokan-skills && ./install-rokan.sh`
3. ✅ Verify: `rokan status`
4. ✅ Try it: `rokan ask "test"`
5. ✅ Enjoy: `rokan` (launches TUI)

---

## FAQ

**Q: Do I need sudo?**
A: Not for user mode (default). Only system mode (`sudo ./install-rokan.sh system`) needs sudo.

**Q: Where's my data stored?**
A: Everything goes in `~/.rokan/` (your home directory).

**Q: Can I use it offline?**
A: No, it requires internet for the NVIDIA NIM API.

**Q: How do I get an API key?**
A: Free at https://build.nvidia.com (takes 2 minutes).

**Q: Can I run it on older Python?**
A: No, requires Python 3.10+.

**Q: How do I uninstall?**
A: Run `./uninstall-rokan.sh` and choose to keep/delete data.

---

## You're All Set! 🎉

Your Linux system now has **a professional AI assistant software**.

**Ready to go?**

```bash
cd "/home/ruzvad/Music/OpenClaw to Rokan/rokan-skills"
./install-rokan.sh
```

**Questions?** Check the documentation files or run `rokan setup`.

---

*Rokan v2.0.0 - The Player - Linux Edition*
