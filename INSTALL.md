# Rokan Installation Guide for Linux

## Overview

Rokan is a system-level AI assistant for Linux that can be installed in two ways:
- **User Installation** (default) - Install for current user only
- **System Installation** - Install system-wide (requires sudo)

## Prerequisites

- **Python 3.10+** - Required
- **pip** - Python package manager
- **git** (optional) - For cloning the repository

### Quick Check

```bash
python3 --version
pip3 --version
```

## Quick Installation (User Mode)

```bash
# Navigate to rokan-skills directory
cd rokan-skills

# Make install script executable
chmod +x install-rokan.sh

# Run user installation (default)
./install-rokan.sh

# Add to PATH if needed (one-time setup)
export PATH="$HOME/.local/bin:$PATH"
```

## Installation Methods

### Method 1: User Installation (Recommended for Most Users)

Install Rokan only for your user account. No sudo required.

```bash
cd rokan-skills
chmod +x install-rokan.sh
./install-rokan.sh user
```

**Location:**
- Binary: `~/.local/bin/rokan`
- Virtual Environment: `~/.local/opt/rokan/venv`
- Data: `~/.rokan`
- Config: `~/.config/rokan`

**Add to PATH permanently:**
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Method 2: System-Wide Installation

Install Rokan for all users on the system.

```bash
cd rokan-skills
chmod +x install-rokan.sh
sudo ./install-rokan.sh system
```

**Location:**
- Binary: `/usr/local/bin/rokan`
- Virtual Environment: `/opt/rokan/venv`
- Data: `~/.rokan` (still per-user)
- Config: `~/.config/rokan` (still per-user)

## Usage After Installation

### Launch the TUI
```bash
rokan
```

### Command-Line Interface
```bash
# Get status
rokan status

# Show available models
rokan models

# Ask a question
rokan ask "Your question here"

# Ask with specific model
rokan ask --think "Complex question requiring deep reasoning"
rokan ask --code "Write a Python script for..."
rokan ask --fast "Quick summary of..."

# System metrics
rokan system

# Show configuration paths
rokan config

# Run setup wizard
rokan setup
```

## Desktop Integration

After installation, Rokan will have a desktop launcher available in your application menu:
- **Search for "Rokan"** in your desktop launcher
- Or click the installed desktop shortcut

## Service Management

### Enable Auto-Start (User Mode)

```bash
systemctl --user enable rokan
systemctl --user start rokan
systemctl --user status rokan
```

### Enable Auto-Start (System Mode)

```bash
sudo systemctl enable rokan
sudo systemctl start rokan
sudo systemctl status rokan
```

### View Service Logs

```bash
# User mode
journalctl --user -u rokan -f

# System mode
sudo journalctl -u rokan -f
```

## Directory Structure

```
~/.rokan/
├── logs/          # Application logs
├── cache/         # Cache files
└── data/          # Application data

~/.config/rokan/   # Configuration files

.local/
├── bin/           # Executable (user mode only)
└── opt/rokan/     # Virtual environment (user mode only)
```

## Configuration

### API Keys

Set your NVIDIA API key for full functionality:

```bash
export NVIDIA_API_KEY="your-api-key-here"
```

Add to `~/.bashrc` or `~/.zshrc` for persistence:
```bash
echo 'export NVIDIA_API_KEY="your-api-key-here"' >> ~/.bashrc
```

## Troubleshooting

### Command Not Found

If you get "rokan: command not found" after user installation:

```bash
# Add to PATH
export PATH="$HOME/.local/bin:$PATH"

# Or add permanently to ~/.bashrc
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Python Module Errors

Ensure all dependencies are installed:

```bash
pip install -r requirements.txt
```

### Permission Denied

Make installation scripts executable:

```bash
chmod +x install-rokan.sh
chmod +x uninstall-rokan.sh
```

### Virtual Environment Issues

Recreate the virtual environment:

```bash
# User mode
rm -rf ~/.local/opt/rokan/venv
./install-rokan.sh user

# System mode
sudo rm -rf /opt/rokan/venv
sudo ./install-rokan.sh system
```

## Uninstallation

### User Mode

```bash
cd rokan-skills
chmod +x uninstall-rokan.sh
./uninstall-rokan.sh user
```

### System Mode

```bash
cd rokan-skills
chmod +x uninstall-rokan.sh
sudo ./uninstall-rokan.sh system
```

## Updating Rokan

```bash
cd rokan-skills
git pull origin main        # Update from source

# User mode
./install-rokan.sh user     # Reinstall

# System mode
sudo ./install-rokan.sh system
```

## Environment Variables

### Required
- `NVIDIA_API_KEY` - For NVIDIA NIM models (get from https://build.nvidia.com)

### Optional
- `GROQ_API_KEY` - Alternative LLM provider
- `TAVILY_API_KEY` - Web search capability

## System Requirements

| Component | Requirement |
|-----------|-------------|
| Python | 3.10+ |
| RAM | 2GB minimum (4GB+ recommended) |
| Disk | 500MB for installation + models |
| OS | Any Linux distribution |

## Getting Help

### View Available Commands
```bash
rokan --help
rokan ask --help
```

### Check System Status
```bash
rokan status
rokan config
```

### Generate Logs
```bash
tail -f ~/.rokan/logs/*
```

## First Run

1. **Set API Key** (optional but recommended)
   ```bash
   export NVIDIA_API_KEY="nvapi-..."
   ```

2. **Verify Installation**
   ```bash
   rokan status
   ```

3. **Launch TUI**
   ```bash
   rokan
   ```

4. **Try a Command**
   ```bash
   rokan ask "What is 2+2?"
   ```

## Advanced Usage

### Running as a Daemon (User Mode)

```bash
systemctl --user enable rokan
systemctl --user start rokan
```

Then access via:
```bash
rokan ask "question"  # CLI commands still work
```

### Custom Installation Path (Manual)

If you prefer to customize the installation:

```bash
# Create virtual environment
python3 -m venv /path/to/rokan-venv

# Activate and install
source /path/to/rokan-venv/bin/activate
cd rokan-skills
pip install -e .

# Create symlink
ln -s /path/to/rokan-venv/bin/python /usr/local/bin/rokan-python
```

---

**Rokan is ready. Execute.**
