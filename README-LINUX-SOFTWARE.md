# 🎯 Rokan — The Player (Linux Software)

**Summit Level System | Sung Jin-Woo Edition | NVIDIA NIM Powered**

Rokan is a production-ready Linux AI assistant that combines real-time system monitoring, advanced reasoning, and a beautiful TUI interface. Install it as a native Linux application.

## 🚀 What You Get

| Feature | Details |
|---------|---------|
| **CLI Tool** | Instant command-line access to every feature |
| **TUI Interface** | Beautiful terminal UI with system monitoring |
| **4 AI Models** | Primary (Llama 70B), Reasoning (GLM 4.7), Fast (Step 3.5), Code (QwQ 32B) |
| **Desktop Launcher** | Click to launch from your app menu |
| **Service Manager** | Optional systemd integration for auto-start |
| **Package Manager** | Installable via pip, manages dependencies |
| **Linux Native** | Uses systemd, .desktop files, Linux standards |

## 📦 Installation

### Quick Start (User Mode - Recommended)

```bash
# Clone or extract the package
cd rokan-skills

# Install (no sudo needed)
./install-rokan.sh

# Done! Use it:
rokan
```

### System-Wide Installation

```bash
cd rokan-skills
sudo ./install-rokan.sh system
```

See [INSTALL.md](INSTALL.md) for detailed instructions.

## 💻 Usage After Installation

### Launch TUI
```bash
rokan    # Launches the beautiful terminal UI
```

### CLI Commands
```bash
rokan ask "What's on my system?"                    # Default (fast)
rokan ask --think "Deep analysis of..."             # Reasoning model
rokan ask --code "Write Python to..."               # Code model
rokan ask --fast "Quick summary of..."              # Ultra-fast

rokan status                                         # System overview
rokan models                                         # Show model stack
rokan system                                         # Live metrics
rokan setup                                          # Initial setup
```

### Desktop Integration
After installation, search for "Rokan" in your application menu to launch the TUI.

## 🏗️ Installation Methods

### Method 1: User Installation (Default)
- **No sudo required**
- Installs in `~/.local/bin/rokan`
- Data stored in `~/.rokan/`
- Perfect for single-user systems

```bash
./install-rokan.sh user
# or just: ./install-rokan.sh
```

### Method 2: System Installation
- **Requires sudo**
- Installs in `/usr/local/bin/rokan`
- Available to all users
- Perfect for multi-user systems

```bash
sudo ./install-rokan.sh system
```

## 📁 Directory Structure

After installation:

```
~/.local/bin/
└── rokan              # Executable (user mode)

~/.local/opt/rokan/    # User mode only
└── venv/              # Python virtual environment

/usr/local/bin/
└── rokan              # Executable (system mode)

/opt/rokan/            # System mode only
└── venv/              # Python virtual environment

~/.rokan/              # Shared across both modes
├── logs/              # Application logs
├── cache/             # Cache files
└── data/              # Application data

~/.config/rokan/       # Configuration files
```

## ⚙️ System Integration

### Auto-Start on Boot (Optional)

**User mode:**
```bash
systemctl --user enable rokan
systemctl --user start rokan
```

**System mode:**
```bash
sudo systemctl enable rokan
sudo systemctl start rokan
```

### View Logs
```bash
journalctl --user -u rokan -f    # User mode
sudo journalctl -u rokan -f       # System mode
```

### Stop Service
```bash
systemctl --user stop rokan       # User mode
sudo systemctl stop rokan          # System mode
```

## 🔧 Configuration

### Set API Key (Optional)
```bash
export NVIDIA_API_KEY="nvapi-..."
```

Add to `~/.bashrc` for persistence:
```bash
echo 'export NVIDIA_API_KEY="nvapi-..."' >> ~/.bashrc
```

## 📋 File Manifest

```
rokan-skills/
├── install-rokan.sh          # Installation script
├── uninstall-rokan.sh        # Uninstallation script
├── INSTALL.md                # Detailed installation guide
├── README.md                 # Feature overview
├── setup.py                  # Python package definition
├── requirements.txt          # Python dependencies
│
├── rokan_cli/                # Command-line interface
│   ├── __init__.py
│   └── main.py               # Entry point (rokan command)
│
├── rokan_tui/                # Terminal UI
│   ├── __init__.py
│   ├── app.py                # Main TUI application
│   ├── nvidia_client.py      # NVIDIA NIM integration
│   ├── system_monitor.py     # System metrics
│   ├── voice.py              # Voice output
│   ├── search.py             # Web search
│   └── styles.tcss           # UI styling
│
├── rokan-memory/             # Semantic memory system
├── rokan-voice/              # Voice I/O pipeline
├── rokan-research/           # Research agent
├── rokan-jobs/               # Job monitoring
├── rokan-system/             # System control
├── rokan-code/               # Code execution
├── rokan-vcr/                # Time-travel debugger
└── rokan_tui.egg-info/       # Package metadata
```

## 🚀 Installation Walkthrough

### 1. **Check Prerequisites**
```bash
python3 --version  # Should be 3.10+
pip3 --version
```

### 2. **Install**
```bash
cd rokan-skills
chmod +x install-rokan.sh
./install-rokan.sh
```

### 3. **Verify Installation**
```bash
rokan status

# Output example:
# ╔══════════════════════════════════════════╗
# ║          ROKAN — Status Report           ║
# ╠══════════════════════════════════════════╣
# ║  Version:    2.0.0                       ║
# ║  NVIDIA NIM: ✓ ACTIVE                    ║
# ║  CPU:          42.3%                     ║
# ╚══════════════════════════════════════════╝
```

### 4. **Launch TUI**
```bash
rokan

# Opens beautiful terminal interface with:
# - Real-time system stats
# - Chat with AI models
# - Model switching commands (/think, /code, /fast)
# - Voice output toggle
```

### 5. **Set API Key** (Optional but Recommended)
```bash
export NVIDIA_API_KEY="nvapi-..."
# Get free key at: https://build.nvidia.com
```

## 🔄 Updating

```bash
cd rokan-skills
git pull              # Get latest version
./install-rokan.sh    # Reinstall (updated)
```

## 🗑️ Uninstall

```bash
cd rokan-skills
./uninstall-rokan.sh

# Choose whether to keep or remove:
# - Binary/venv (always removed)
# - Data directory (prompted)
```

## ❓ Troubleshooting

### "rokan: command not found"
```bash
export PATH="$HOME/.local/bin:$PATH"
# Add to ~/.bashrc for permanent fix
```

### "NVIDIA_API_KEY not found"
```bash
export NVIDIA_API_KEY="nvapi-..."
rokan ask "test"
```

### Python errors
```bash
pip install -r requirements.txt
```

See [INSTALL.md](INSTALL.md) for more troubleshooting.

## 📊 System Requirements

| Component | Requirement |
|-----------|-------------|
| OS | Any Linux distro (Ubuntu, Fedora, Arch, etc.) |
| Python | 3.10+ |
| RAM | 2GB min, 4GB+ recommended |
| Disk | 500MB for installation |
| Internet | Required for NVIDIA NIM API |

## 🌟 Key Features

### 1. **Multi-Model AI**
- Primary: Llama 3.3 70B (general queries)
- Reasoning: GLM 4.7 (deep analysis)
- Fast: Step 3.5 Flash (quick answers)
- Code: QwQ 32B (generation & debugging)

### 2. **Beautiful TUI**
```
╔════════════════════════════════════════════╗
║   ROKAN — THE PLAYER                       ║
╠════════════════════════════════════════════╣
║                                            ║
║   > Your question here                     ║
║                                            ║
║   Rokan's response streams in real-time    ║
║   with system metrics on the left sidebar  ║
║                                            ║
╚════════════════════════════════════════════╝
```

### 3. **Native Linux Integration**
- ✓ systemd services
- ✓ Desktop launcher (.desktop file)
- ✓ Virtual environment management
- ✓ Standard Linux file layout

### 4. **Slash Commands in TUI**
- `/think` - Use reasoning model
- `/code` - Use code model
- `/fast` - Use fast model
- `/voice` - Toggle voice output
- `/clear` - Clear chat history

## 📚 Documentation

| File | Purpose |
|------|---------|
| [INSTALL.md](INSTALL.md) | Detailed installation guide |
| [README.md](README.md) | Feature overview |
| setup.py | Python package configuration |
| requirements.txt | Dependencies list |

## 🎯 Quick Commands Reference

```bash
# Installation
./install-rokan.sh              # User install
sudo ./install-rokan.sh system  # System install

# Usage
rokan                           # Launch TUI
rokan ask "question"            # Ask via CLI
rokan status                    # System status
rokan models                    # Show models
rokan setup                     # Setup wizard

# Service Management
systemctl --user enable rokan   # Enable auto-start
systemctl --user start rokan    # Start service
systemctl --user stop rokan     # Stop service

# Uninstall
./uninstall-rokan.sh            # User uninstall
sudo ./uninstall-rokan.sh system # System uninstall
```

## 🔐 Privacy & Security

- ✓ All processing local (no cloud leaks)
- ✓ API keys stored in environment variables
- ✓ Data directories in user home (~/.rokan)
- ✓ No telemetry or tracking
- ✓ Open source (transparency)

## 🎮 Advanced Usage

### Run as Background Daemon
```bash
systemctl --user enable rokan
systemctl --user start rokan

# Still use CLI commands:
rokan ask "something"
```

### View Real-Time Logs
```bash
journalctl --user -u rokan -f
```

### Custom Virtual Environment
See [INSTALL.md](INSTALL.md) for manual installation options.

## 🤝 Support

### Check Installation
```bash
rokan setup
```

### View System Info
```bash
rokan status
rokan system
```

### Get Help
```bash
rokan --help
rokan ask --help
```

---

## 📝 Version Info

- **Rokan Version:** 2.0.0
- **NVIDIA NIM:** Integrated
- **Python:** 3.10+
- **Platform:** Linux (all distributions)

---

**Rokan is ready. Execute.**

For detailed setup, see [INSTALL.md](INSTALL.md)
