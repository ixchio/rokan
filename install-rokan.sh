#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# Rokan v3.0 — Full Desktop Installer for Linux
# Installs EVERYTHING:
#   - Python deps (voice, STT, TTS, wake word, search, LLM)
#   - System packages (screen awareness, screenshots, audio, calendar)
#   - Electron desktop app
#   - Desktop entry + overlay widget
#   - Interactive setup wizard (API keys, email, calendar)
#   - systemd auto-start service
#
# Usage:
#   ./install-rokan.sh          # User install (recommended)
#   sudo ./install-rokan.sh system  # System-wide install
# ═══════════════════════════════════════════════════════════════════

ROKAN_VERSION="3.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_TYPE="${1:-user}"

# Colors
R='\033[0;31m' G='\033[0;32m' Y='\033[1;33m' B='\033[0;34m' C='\033[0;36m' N='\033[0m' W='\033[1;37m'
ok()   { echo -e "${G}[+]${N} $1"; }
info() { echo -e "${B}[*]${N} $1"; }
warn() { echo -e "${Y}[!]${N} $1"; }
fail() { echo -e "${R}[x]${N} $1"; }
ask()  { echo -en "${W}[?]${N} $1"; }

# ── Paths ────────────────────────────────────────────────────────
if [ "$INSTALL_TYPE" = "system" ]; then
    VENV="/opt/rokan/venv"
    BIN_DIR="/usr/local/bin"
    DESKTOP_DIR="/usr/share/applications"
    SERVICE_DIR="/etc/systemd/system"
    ICON_DIR="/usr/share/icons/hicolor/256x256/apps"
else
    VENV="$HOME/.local/opt/rokan/venv"
    BIN_DIR="$HOME/.local/bin"
    DESKTOP_DIR="$HOME/.local/share/applications"
    SERVICE_DIR="$HOME/.config/systemd/user"
    ICON_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"
fi
DATA_DIR="$HOME/.rokan"
CONFIG_DIR="$HOME/.config/rokan"
ENV_FILE="$DATA_DIR/.env"

# ── Banner ───────────────────────────────────────────────────────
banner() {
    echo -e "${W}"
    cat << 'EOF'

   ██████╗  ██████╗ ██╗  ██╗ █████╗ ███╗   ██╗
   ██╔══██╗██╔═══██╗██║ ██╔╝██╔══██╗████╗  ██║
   ██████╔╝██║   ██║█████╔╝ ███████║██╔██╗ ██║
   ██╔══██╗██║   ██║██╔═██╗ ██╔══██║██║╚██╗██║
   ██║  ██║╚██████╔╝██║  ██╗██║  ██║██║ ╚████║
   ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝

   v3.0 — F.R.I.D.A.Y.-class Ambient Intelligence
EOF
    echo -e "${N}"
}

# ── Step 1: Check Python ────────────────────────────────────────
check_python() {
    info "Checking Python..."

    if ! command -v python3 &> /dev/null; then
        fail "Python 3 not found. Install it:"
        echo "  Ubuntu/Debian:  sudo apt install python3 python3-venv python3-pip"
        echo "  Fedora:         sudo dnf install python3 python3-pip"
        echo "  Arch:           sudo pacman -S python python-pip"
        exit 1
    fi

    PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
    PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)

    if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
        fail "Python 3.10+ required. Found: $PY_VER"
        exit 1
    fi

    if ! python3 -c "import venv" 2>/dev/null; then
        fail "python3-venv not found. Install it:"
        echo "  Ubuntu/Debian:  sudo apt install python3-venv"
        exit 1
    fi

    ok "Python $PY_VER"
}

# ── Step 2: Install ALL system packages ─────────────────────────
install_system_deps() {
    info "Installing system packages (voice, screen awareness, calendar, audio)..."

    if command -v apt &> /dev/null; then
        PKGS=""

        # Audio playback (voice output)
        command -v mpv     &>/dev/null || PKGS="$PKGS mpv"

        # Audio recording (voice input) — portaudio for sounddevice
        dpkg -s libportaudio2    &>/dev/null || PKGS="$PKGS libportaudio2"
        dpkg -s portaudio19-dev  &>/dev/null || PKGS="$PKGS portaudio19-dev"

        # Screen awareness
        command -v xdotool    &>/dev/null || PKGS="$PKGS xdotool"
        command -v xprintidle &>/dev/null || PKGS="$PKGS xprintidle"

        # Screenshots + OCR
        command -v scrot     &>/dev/null || PKGS="$PKGS scrot"
        command -v tesseract &>/dev/null || PKGS="$PKGS tesseract-ocr"

        # Calendar
        command -v calcurse &>/dev/null || PKGS="$PKGS calcurse"

        # Desktop notifications
        command -v notify-send &>/dev/null || PKGS="$PKGS libnotify-bin"

        # Clipboard
        command -v xclip &>/dev/null || PKGS="$PKGS xclip"

        # Node.js for Electron (if not present)
        command -v node &>/dev/null || command -v nodejs &>/dev/null || PKGS="$PKGS nodejs npm"

        # Python headers (needed for some pip packages)
        dpkg -s python3-dev &>/dev/null || PKGS="$PKGS python3-dev"

        if [ -n "$PKGS" ]; then
            info "Installing:$PKGS"
            sudo apt update -qq 2>/dev/null
            sudo apt install -y $PKGS 2>/dev/null && ok "All system packages installed" || {
                warn "Some packages failed. Try manually:"
                echo "  sudo apt install$PKGS"
            }
        else
            ok "All system packages already present"
        fi

    elif command -v dnf &> /dev/null; then
        sudo dnf install -y mpv portaudio-devel xdotool xprintidle scrot \
            tesseract calcurse libnotify xclip nodejs python3-devel 2>/dev/null \
            && ok "System packages installed" \
            || warn "Some packages failed. Install manually."

    elif command -v pacman &> /dev/null; then
        sudo pacman -S --noconfirm mpv portaudio xdotool xprintidle scrot \
            tesseract calcurse libnotify xclip nodejs python 2>/dev/null \
            && ok "System packages installed" \
            || warn "Some packages failed. Install manually."
    else
        warn "Unknown distro. Install these manually:"
        echo "  mpv portaudio xdotool xprintidle scrot tesseract calcurse xclip"
    fi
}

# ── Step 3: Create venv + install Rokan ─────────────────────────
install_rokan() {
    info "Creating virtual environment..."
    mkdir -p "$(dirname "$VENV")"

    if [ ! -d "$VENV" ]; then
        python3 -m venv --system-site-packages "$VENV"
        ok "Venv created: $VENV"
    else
        ok "Venv exists: $VENV"
    fi

    info "Installing Rokan + all Python deps (voice, STT, search, LLM)..."
    "$VENV/bin/pip" install --upgrade pip setuptools wheel -q
    "$VENV/bin/pip" install -e "$SCRIPT_DIR" -q 2>&1 | tail -3

    ok "Rokan v$ROKAN_VERSION installed with all dependencies"
}

# ── Step 4: Install Electron ────────────────────────────────────
install_electron() {
    if [ ! -d "$SCRIPT_DIR/electron" ]; then
        warn "No electron/ directory found, skipping desktop app build"
        return
    fi

    info "Installing Electron desktop app..."
    cd "$SCRIPT_DIR/electron"

    if command -v npm &>/dev/null; then
        npm install --silent 2>/dev/null && ok "Electron dependencies installed" || warn "npm install failed"
    else
        warn "npm not found. Electron desktop app won't work."
        warn "Install Node.js: sudo apt install nodejs npm"
    fi

    cd "$SCRIPT_DIR"
}

# ── Step 5: Create launcher ─────────────────────────────────────
create_launcher() {
    info "Creating launcher: ${BIN_DIR}/rokan"
    mkdir -p "$BIN_DIR"

    cat > "${BIN_DIR}/rokan" << LAUNCHER
#!/bin/bash
# Rokan v3.0 — F.R.I.D.A.Y.
if [ -f "$DATA_DIR/.env" ]; then
    set -a; source "$DATA_DIR/.env"; set +a
fi
source "$VENV/bin/activate"
exec python -m rokan_cli.main "\$@"
LAUNCHER

    chmod +x "${BIN_DIR}/rokan"
    ok "Launcher: ${BIN_DIR}/rokan"
}

# ── Step 6: Create .desktop file ────────────────────────────────
create_desktop_entry() {
    info "Creating desktop app entry..."
    mkdir -p "$DESKTOP_DIR"

    cat > "${DESKTOP_DIR}/rokan.desktop" << DESKTOP
[Desktop Entry]
Version=3.0
Type=Application
Name=Rokan
GenericName=AI Assistant
Comment=F.R.I.D.A.Y.-class ambient intelligence
Exec=bash -c 'if [ -f $DATA_DIR/.env ]; then set -a; source $DATA_DIR/.env; set +a; fi; source $VENV/bin/activate && python -m rokan_gui.window'
Icon=rokan
Terminal=false
Categories=Development;Utility;System;
Keywords=AI;Assistant;FRIDAY;Voice;
StartupNotify=true
StartupWMClass=rokan
DESKTOP

    chmod 644 "${DESKTOP_DIR}/rokan.desktop"
    update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true

    ok "Desktop entry created (search 'Rokan' in app menu)"
}

# ── Step 7: Create icon ─────────────────────────────────────────
create_icon() {
    info "Creating app icon..."
    mkdir -p "$ICON_DIR"

    cat > "${ICON_DIR}/rokan.svg" << 'ICON'
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256">
  <rect width="256" height="256" rx="48" fill="#111"/>
  <rect x="8" y="8" width="240" height="240" rx="40" fill="none" stroke="#555" stroke-width="2"/>
  <text x="128" y="148" font-family="monospace" font-size="96" font-weight="bold" fill="#999" text-anchor="middle">R</text>
  <circle cx="128" cy="210" r="6" fill="#666"/>
</svg>
ICON

    gtk-update-icon-cache -f -t "$(dirname "$(dirname "$ICON_DIR")")" 2>/dev/null || true
    ok "App icon installed"
}

# ── Step 8: Create data dirs ────────────────────────────────────
create_data_dirs() {
    info "Creating data directories..."
    mkdir -p "$DATA_DIR"/{logs,cache}
    mkdir -p "$CONFIG_DIR"

    if [ ! -f "$CONFIG_DIR/config.yaml" ] && [ -f "$SCRIPT_DIR/config.yaml" ]; then
        cp "$SCRIPT_DIR/config.yaml" "$CONFIG_DIR/config.yaml"
    fi

    ok "Data: $DATA_DIR"
}

# ── Step 9: Setup Wizard (interactive credentials) ──────────────
setup_wizard() {
    echo ""
    echo -e "${W}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
    echo -e "${W}  ROKAN SETUP WIZARD${N}"
    echo -e "${W}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
    echo ""

    # Start fresh or preserve existing
    if [ -f "$ENV_FILE" ]; then
        # Source existing values so we can show defaults
        set -a; source "$ENV_FILE" 2>/dev/null; set +a
        info "Found existing config at $ENV_FILE"
    fi

    # Start building env file
    ENV_CONTENT="# Rokan v3.0 — Configuration\n# Auto-generated by setup wizard\n\n"

    # ── NVIDIA API Key ────────────────────────────────────────
    echo -e "${W}1. NVIDIA API KEY${N} (powers the AI brain)"
    echo "   Get a free key at: https://build.nvidia.com"
    echo "   Sign up -> any model page -> 'Get API Key'"
    echo ""
    ask "NVIDIA API key [${NVIDIA_API_KEY:+already set}]: "
    read -r input_nvidia
    if [ -n "$input_nvidia" ]; then
        NVIDIA_API_KEY="$input_nvidia"
    fi
    if [ -n "$NVIDIA_API_KEY" ]; then
        ENV_CONTENT+="NVIDIA_API_KEY=$NVIDIA_API_KEY\n"
        ok "NVIDIA key set"
    else
        ENV_CONTENT+="# NVIDIA_API_KEY=nvapi-your-key-here\n"
        warn "No key set. LLM won't work but 20 skills still function."
    fi
    echo ""

    # ── Email (Gmail) ─────────────────────────────────────────
    echo -e "${W}2. EMAIL (Gmail inbox access)${N}"
    echo "   Rokan can check your inbox, summarize unread emails."
    echo "   For Gmail you need an App Password (NOT your real password):"
    echo "   1. Go to https://myaccount.google.com/apppasswords"
    echo "   2. Select 'Mail' and your device"
    echo "   3. Copy the 16-character password"
    echo ""
    ask "Gmail address [${IMAP_USER:-skip}]: "
    read -r input_email
    if [ -n "$input_email" ]; then
        IMAP_USER="$input_email"
        IMAP_SERVER="imap.gmail.com"

        ask "Gmail App Password (16 chars, no spaces): "
        read -rs input_pass
        echo ""
        if [ -n "$input_pass" ]; then
            IMAP_PASSWORD="$input_pass"
            ENV_CONTENT+="\n# Email\nIMAP_SERVER=imap.gmail.com\nIMAP_USER=$IMAP_USER\nIMAP_PASSWORD=$IMAP_PASSWORD\n"
            ok "Email configured: $IMAP_USER"
        else
            warn "No password. Email skill won't work."
        fi
    else
        if [ -n "$IMAP_USER" ]; then
            ENV_CONTENT+="\n# Email\nIMAP_SERVER=${IMAP_SERVER:-imap.gmail.com}\nIMAP_USER=$IMAP_USER\nIMAP_PASSWORD=$IMAP_PASSWORD\n"
            ok "Keeping existing email config: $IMAP_USER"
        else
            info "Skipped email setup."
        fi
    fi
    echo ""

    # ── Calendar ──────────────────────────────────────────────
    echo -e "${W}3. CALENDAR${N}"
    if command -v calcurse &>/dev/null; then
        ok "calcurse is installed. Add events with: calcurse"
    fi
    if command -v gcalcli &>/dev/null; then
        ok "gcalcli is installed (Google Calendar)"
    else
        echo "   For Google Calendar integration:"
        echo "   pip install gcalcli && gcalcli init"
        ask "Install gcalcli now? [y/N]: "
        read -r input_gcal
        if [[ "$input_gcal" =~ ^[Yy] ]]; then
            "$VENV/bin/pip" install gcalcli -q 2>/dev/null && ok "gcalcli installed" || warn "gcalcli install failed"
            echo ""
            echo "   Run 'gcalcli init' after install to connect your Google account."
        fi
    fi
    echo ""

    # ── Write env file ────────────────────────────────────────
    echo -e "$ENV_CONTENT" > "$ENV_FILE"
    chmod 600 "$ENV_FILE"
    ok "Config saved to $ENV_FILE (permissions: 600)"
}

# ── Step 10: Create systemd service ─────────────────────────────
create_service() {
    info "Creating systemd service..."
    mkdir -p "$SERVICE_DIR"

    if [ "$INSTALL_TYPE" = "system" ]; then
        SVCUSER="User=$USER"
    else
        SVCUSER=""
    fi

    cat > "${SERVICE_DIR}/rokan.service" << SERVICE
[Unit]
Description=Rokan — F.R.I.D.A.Y. Ambient Intelligence
After=network.target graphical-session.target
Wants=graphical-session.target

[Service]
Type=simple
${SVCUSER}
WorkingDirectory=$HOME
EnvironmentFile=-$DATA_DIR/.env
Environment="PATH=$VENV/bin:/usr/local/bin:/usr/bin"
ExecStart=$VENV/bin/python -m rokan_gui.server
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
SERVICE

    chmod 644 "${SERVICE_DIR}/rokan.service"

    if [ "$INSTALL_TYPE" != "system" ]; then
        systemctl --user daemon-reload 2>/dev/null || true
    fi

    ok "Service: ${SERVICE_DIR}/rokan.service"
}

# ── Step 11: PATH check ─────────────────────────────────────────
check_path() {
    if echo "$PATH" | grep -q "$BIN_DIR"; then
        return
    fi

    SHELL_NAME=$(basename "$SHELL")
    case "$SHELL_NAME" in
        bash) RC="$HOME/.bashrc" ;;
        zsh)  RC="$HOME/.zshrc" ;;
        fish) RC="$HOME/.config/fish/config.fish" ;;
        *)    RC="" ;;
    esac

    if [ -n "$RC" ] && [ -f "$RC" ]; then
        if ! grep -q "$BIN_DIR" "$RC" 2>/dev/null; then
            echo "" >> "$RC"
            echo "# Rokan" >> "$RC"
            echo "export PATH=\"$BIN_DIR:\$PATH\"" >> "$RC"
            ok "Added $BIN_DIR to $RC"
        fi
    fi
}

# ── Verification ─────────────────────────────────────────────────
verify_install() {
    echo ""
    info "Verifying installation..."
    echo ""

    "$VENV/bin/python" -c "
from rokan_core.agent import RokanAgent
a = RokanAgent()
skills = a.skills.list_skills()
print(f'  skills:       {len(skills)}')
print(f'  voice:        {\"ready\" if a.voice else \"missing deps\"}')
print(f'  screen:       {\"ready\" if a.screen else \"missing deps\"}')
print(f'  automations:  {\"ready\" if a.automations else \"missing deps\"}')
print(f'  llm:          {\"online\" if a.is_llm_available else \"no api key\"}')
" 2>/dev/null

    echo ""

    # Check system tools
    for tool in xdotool xprintidle scrot tesseract mpv xclip calcurse notify-send; do
        if command -v "$tool" &>/dev/null; then
            echo -e "  ${G}+${N} $tool"
        else
            echo -e "  ${R}-${N} $tool (missing)"
        fi
    done

    echo ""
}

# ── Summary ──────────────────────────────────────────────────────
summary() {
    echo ""
    echo -e "${W}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
    echo -e "${W}  ROKAN v3.0 — INSTALLED${N}"
    echo -e "${W}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
    echo ""
    echo "  command:     rokan"
    echo "  config:      $ENV_FILE"
    echo "  data:        $DATA_DIR"
    echo ""
    echo "  usage:"
    echo "    rokan                   terminal UI"
    echo "    rokan ask \"hello\"       quick question"
    echo "    rokan status            system check"
    echo ""
    echo "  desktop:"
    echo "    search 'Rokan' in app menu"
    echo "    or: cd $SCRIPT_DIR/electron && npm start"
    echo ""

    if [ "$INSTALL_TYPE" = "system" ]; then
        echo "  auto-start:"
        echo "    sudo systemctl enable --now rokan"
    else
        echo "  auto-start:"
        echo "    systemctl --user enable --now rokan"
    fi

    echo ""
}

# ── Main ─────────────────────────────────────────────────────────
main() {
    banner

    if [ "$INSTALL_TYPE" = "system" ] && [ "$EUID" -ne 0 ]; then
        fail "System install needs root: sudo ./install-rokan.sh system"
        exit 1
    fi

    info "Installing Rokan v$ROKAN_VERSION ($INSTALL_TYPE mode)"
    echo ""

    check_python
    install_system_deps
    install_rokan
    install_electron
    create_launcher
    create_desktop_entry
    create_icon
    create_data_dirs
    setup_wizard
    create_service
    check_path
    verify_install

    summary
}

main "$@"
