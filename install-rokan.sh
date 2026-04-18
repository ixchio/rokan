#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# Rokan — Desktop App Installer for Linux
# Installs as a real desktop application:
#   • CLI command: rokan
#   • Desktop app in your app menu (GNOME/KDE/XFCE/etc)
#   • Optional systemd service (auto-start)
#   • Voice playback support (mpv)
#
# Usage:
#   ./install-rokan.sh          # User install (recommended)
#   sudo ./install-rokan.sh system  # System-wide install
# ═══════════════════════════════════════════════════════════════════

ROKAN_VERSION="2.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_TYPE="${1:-user}"

# Colors
R='\033[0;31m' G='\033[0;32m' Y='\033[1;33m' B='\033[0;34m' C='\033[0;36m' N='\033[0m'
ok()   { echo -e "${G}[✓]${N} $1"; }
info() { echo -e "${B}[*]${N} $1"; }
warn() { echo -e "${Y}[!]${N} $1"; }
fail() { echo -e "${R}[✗]${N} $1"; }

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

# ── Banner ───────────────────────────────────────────────────────
banner() {
    echo -e "${C}"
    cat << 'EOF'

   ██████╗  ██████╗ ██╗  ██╗ █████╗ ███╗   ██╗
   ██╔══██╗██╔═══██╗██║ ██╔╝██╔══██╗████╗  ██║
   ██████╔╝██║   ██║█████╔╝ ███████║██╔██╗ ██║
   ██╔══██╗██║   ██║██╔═██╗ ██╔══██║██║╚██╗██║
   ██║  ██║╚██████╔╝██║  ██╗██║  ██║██║ ╚████║
   ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝

   Desktop Installer v2.0 — The System
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

    # Check for venv module
    if ! python3 -c "import venv" 2>/dev/null; then
        fail "python3-venv not found. Install it:"
        echo "  Ubuntu/Debian:  sudo apt install python3-venv"
        exit 1
    fi

    ok "Python $PY_VER"
}

# ── Step 2: Install system deps (GTK window + voice) ───────────
install_system_deps() {
    info "Installing system dependencies for native desktop app..."

    if command -v apt &> /dev/null; then
        # Ubuntu / Debian
        PKGS=""

        # GTK + WebKit for native window (THE important ones)
        dpkg -s python3-gi &>/dev/null       || PKGS="$PKGS python3-gi"
        dpkg -s python3-gi-cairo &>/dev/null  || PKGS="$PKGS python3-gi-cairo"
        dpkg -s gir1.2-gtk-3.0 &>/dev/null   || PKGS="$PKGS gir1.2-gtk-3.0"

        # Try webkit 4.1 first (Ubuntu 22.04+), fallback to 4.0
        if ! dpkg -s gir1.2-webkit2-4.1 &>/dev/null && ! dpkg -s gir1.2-webkit2-4.0 &>/dev/null; then
            PKGS="$PKGS gir1.2-webkit2-4.1"
        fi

        # Voice playback
        command -v mpv &>/dev/null || PKGS="$PKGS mpv"

        if [ -n "$PKGS" ]; then
            info "Installing:$PKGS"
            sudo apt update -qq 2>/dev/null
            sudo apt install -y $PKGS 2>/dev/null && ok "System packages installed" || {
                fail "Could not install some packages. Run manually:"
                echo "  sudo apt install$PKGS"
            }
        else
            ok "All system packages present"
        fi

    elif command -v dnf &> /dev/null; then
        # Fedora
        sudo dnf install -y python3-gobject gtk3 webkit2gtk4.1 mpv 2>/dev/null \
            && ok "System packages installed" \
            || warn "Install manually: sudo dnf install python3-gobject gtk3 webkit2gtk4.1 mpv"

    elif command -v pacman &> /dev/null; then
        # Arch
        sudo pacman -S --noconfirm python-gobject gtk3 webkit2gtk-4.1 mpv 2>/dev/null \
            && ok "System packages installed" \
            || warn "Install manually: sudo pacman -S python-gobject gtk3 webkit2gtk-4.1 mpv"
    else
        warn "Unknown distro. Install these manually:"
        echo "  python3-gi, gir1.2-gtk-3.0, gir1.2-webkit2-4.1, mpv"
    fi
}

# ── Step 3: Create venv + install Rokan ─────────────────────────
install_rokan() {
    info "Creating virtual environment..."
    mkdir -p "$(dirname "$VENV")"

    if [ ! -d "$VENV" ]; then
        # --system-site-packages: lets venv access system GTK/WebKit bindings
        python3 -m venv --system-site-packages "$VENV"
        ok "Venv created: $VENV (with system site-packages for GTK)"
    else
        ok "Venv exists: $VENV"
    fi

    info "Installing Rokan and dependencies..."
    "$VENV/bin/pip" install --upgrade pip setuptools wheel -q
    "$VENV/bin/pip" install -e "$SCRIPT_DIR" -q

    # Optional: install search support
    "$VENV/bin/pip" install duckduckgo-search -q 2>/dev/null || true

    ok "Rokan v$ROKAN_VERSION installed"
}

# ── Step 4: Create launcher script ──────────────────────────────
create_launcher() {
    info "Creating launcher: ${BIN_DIR}/rokan"
    mkdir -p "$BIN_DIR"

    cat > "${BIN_DIR}/rokan" << LAUNCHER
#!/bin/bash
# Rokan — The System
# Auto-generated launcher. Loads env, activates venv, runs rokan.

# Load API keys
if [ -f "$DATA_DIR/.env" ]; then
    set -a
    source "$DATA_DIR/.env"
    set +a
fi

source "$VENV/bin/activate"
exec python -m rokan_cli.main "\$@"
LAUNCHER

    chmod +x "${BIN_DIR}/rokan"
    ok "Launcher: ${BIN_DIR}/rokan"
}

# ── Step 5: Create .desktop file (app menu entry) ──────────────
create_desktop_entry() {
    info "Creating desktop app entry..."
    mkdir -p "$DESKTOP_DIR"

    cat > "${DESKTOP_DIR}/rokan.desktop" << DESKTOP
[Desktop Entry]
Version=2.0
Type=Application
Name=Rokan
GenericName=AI Assistant
Comment=F.R.I.D.A.Y.-class ambient intelligence for your machine
Exec=bash -c 'if [ -f $DATA_DIR/.env ]; then set -a; source $DATA_DIR/.env; set +a; fi; source $VENV/bin/activate && python -m rokan_gui.window'
Icon=rokan
Terminal=false
Categories=Development;Utility;System;
Keywords=AI;Assistant;LLM;System;Monitor;
StartupNotify=true
StartupWMClass=rokan
DESKTOP

    chmod 644 "${DESKTOP_DIR}/rokan.desktop"

    # Validate if desktop-file-validate exists
    if command -v desktop-file-validate &> /dev/null; then
        desktop-file-validate "${DESKTOP_DIR}/rokan.desktop" 2>/dev/null || true
    fi

    # Update desktop database
    if command -v update-desktop-database &> /dev/null; then
        update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
    fi

    ok "Desktop entry: ${DESKTOP_DIR}/rokan.desktop"
    ok "Rokan will appear in your app menu"
}

# ── Step 6: Create icon ─────────────────────────────────────────
create_icon() {
    info "Creating app icon..."
    mkdir -p "$ICON_DIR"

    # Generate a simple SVG icon (terminal + brain aesthetic)
    cat > "${ICON_DIR}/rokan.svg" << 'ICON'
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#04040a"/>
      <stop offset="100%" style="stop-color:#0a0a1a"/>
    </linearGradient>
    <linearGradient id="glow" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#00aaff"/>
      <stop offset="100%" style="stop-color:#4169e1"/>
    </linearGradient>
  </defs>
  <rect width="256" height="256" rx="48" fill="url(#bg)"/>
  <rect x="8" y="8" width="240" height="240" rx="40" fill="none" stroke="url(#glow)" stroke-width="2" opacity="0.4"/>
  <text x="128" y="148" font-family="monospace" font-size="96" font-weight="bold" fill="url(#glow)" text-anchor="middle">R</text>
  <circle cx="128" cy="210" r="6" fill="#00aaff" opacity="0.8"/>
  <circle cx="108" cy="210" r="3" fill="#00aaff" opacity="0.4"/>
  <circle cx="148" cy="210" r="3" fill="#00aaff" opacity="0.4"/>
</svg>
ICON

    # Update icon cache
    if command -v gtk-update-icon-cache &> /dev/null; then
        gtk-update-icon-cache -f -t "$(dirname "$(dirname "$ICON_DIR")")" 2>/dev/null || true
    fi

    ok "App icon installed"
}

# ── Step 7: Create data directories + env template ──────────────
create_data_dirs() {
    info "Creating data directories..."
    mkdir -p "$DATA_DIR"/{logs,cache}
    mkdir -p "$CONFIG_DIR"

    # Copy config if not present
    if [ ! -f "$CONFIG_DIR/config.yaml" ] && [ -f "$SCRIPT_DIR/config.yaml" ]; then
        cp "$SCRIPT_DIR/config.yaml" "$CONFIG_DIR/config.yaml"
        ok "Config copied to $CONFIG_DIR/config.yaml"
    fi

    # Create .env template if not present
    if [ ! -f "$DATA_DIR/.env" ]; then
        cat > "$DATA_DIR/.env" << 'ENV'
# Rokan Environment — Put your API keys here
# This file is auto-loaded when you run rokan.

# REQUIRED — Get free at https://build.nvidia.com
NVIDIA_API_KEY=

# OPTIONAL — For web search (DuckDuckGo works without a key)
# TAVILY_API_KEY=
ENV
        ok "API key file: $DATA_DIR/.env  ← PUT YOUR KEY HERE"
    else
        ok "API key file already exists: $DATA_DIR/.env"
    fi

    ok "Data: $DATA_DIR"
}

# ── Step 8: Create systemd service (optional) ───────────────────
create_service() {
    info "Creating systemd service (optional, for auto-start)..."
    mkdir -p "$SERVICE_DIR"

    if [ "$INSTALL_TYPE" = "system" ]; then
        SVCUSER="User=$USER"
    else
        SVCUSER=""
    fi

    cat > "${SERVICE_DIR}/rokan.service" << SERVICE
[Unit]
Description=Rokan — Ambient Intelligence
After=network.target graphical-session.target
Wants=graphical-session.target

[Service]
Type=simple
${SVCUSER}
WorkingDirectory=$HOME
EnvironmentFile=-$DATA_DIR/.env
Environment="PATH=$VENV/bin:/usr/local/bin:/usr/bin"
ExecStart=$VENV/bin/python -m rokan_cli.main tui
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

# ── Step 9: PATH check ──────────────────────────────────────────
check_path() {
    if echo "$PATH" | grep -q "$BIN_DIR"; then
        return
    fi

    warn "$BIN_DIR is not in your PATH."

    # Auto-fix for common shells
    SHELL_NAME=$(basename "$SHELL")
    case "$SHELL_NAME" in
        bash)
            RC="$HOME/.bashrc"
            ;;
        zsh)
            RC="$HOME/.zshrc"
            ;;
        fish)
            RC="$HOME/.config/fish/config.fish"
            ;;
        *)
            RC=""
            ;;
    esac

    if [ -n "$RC" ] && [ -f "$RC" ]; then
        if ! grep -q "$BIN_DIR" "$RC" 2>/dev/null; then
            echo "" >> "$RC"
            echo "# Rokan" >> "$RC"
            echo "export PATH=\"$BIN_DIR:\$PATH\"" >> "$RC"
            ok "Added $BIN_DIR to $RC"
            warn "Run: source $RC  (or open a new terminal)"
        fi
    else
        warn "Add this to your shell config:"
        echo "  export PATH=\"$BIN_DIR:\$PATH\""
    fi
}

# ── Summary ──────────────────────────────────────────────────────
summary() {
    echo ""
    echo -e "${G}╔═══════════════════════════════════════════════════════════╗${N}"
    echo -e "${G}║              ROKAN v2.0 — INSTALLED                      ║${N}"
    echo -e "${G}╚═══════════════════════════════════════════════════════════╝${N}"
    echo ""
    echo -e "  ${C}Install type:${N}  $INSTALL_TYPE"
    echo -e "  ${C}Command:${N}       ${Y}rokan${N}"
    echo -e "  ${C}Venv:${N}          $VENV"
    echo -e "  ${C}Data:${N}          $DATA_DIR"
    echo -e "  ${C}Config:${N}        $CONFIG_DIR/config.yaml"
    echo -e "  ${C}API keys:${N}      $DATA_DIR/.env"
    echo ""
    echo -e "  ${R}⚠  IMPORTANT — Set your NVIDIA API key:${N}"
    echo ""
    echo -e "  ${Y}nano $DATA_DIR/.env${N}"
    echo -e "  Add: ${Y}NVIDIA_API_KEY=nvapi-your-key-here${N}"
    echo -e "  Get one free at: ${C}https://build.nvidia.com${N}"
    echo ""
    echo -e "  ${B}Quick Start:${N}"
    echo -e "    ${Y}rokan${N}                   Launch TUI (desktop app)"
    echo -e "    ${Y}rokan ask \"hello\"${N}        Ask a question from terminal"
    echo -e "    ${Y}rokan status${N}             Check system status"
    echo -e "    ${Y}rokan setup${N}              Verify all dependencies"
    echo ""
    echo -e "  ${B}Desktop App:${N}"
    echo -e "    Search for ${Y}Rokan${N} in your app menu (GNOME/KDE/etc)"
    echo ""

    if [ "$INSTALL_TYPE" = "system" ]; then
        echo -e "  ${B}Auto-start (optional):${N}"
        echo -e "    ${Y}sudo systemctl enable rokan${N}"
        echo -e "    ${Y}sudo systemctl start rokan${N}"
    else
        echo -e "  ${B}Auto-start (optional):${N}"
        echo -e "    ${Y}systemctl --user enable rokan${N}"
        echo -e "    ${Y}systemctl --user start rokan${N}"
    fi

    echo ""
    echo -e "  ${G}The System is online.${N}"
    echo ""
}

# ── Main ─────────────────────────────────────────────────────────
main() {
    banner

    if [ "$INSTALL_TYPE" = "system" ] && [ "$EUID" -ne 0 ]; then
        fail "System-wide install needs root. Run:"
        echo "  sudo ./install-rokan.sh system"
        exit 1
    fi

    info "Installing Rokan v$ROKAN_VERSION ($INSTALL_TYPE mode)"
    echo ""

    check_python
    install_system_deps
    install_rokan
    create_launcher
    create_desktop_entry
    create_icon
    create_data_dirs
    create_service
    check_path

    summary
}

main "$@"
