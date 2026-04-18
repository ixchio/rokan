#!/bin/bash
# Rokan Installation Script for Linux
# Installs Rokan CLI and TUI as a system software
# Supports both user and system-wide installation

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_TYPE="${1:-user}"  # user or system

print_banner() {
    echo -e "${CYAN}"
    cat << "EOF"
╔════════════════════════════════════════════╗
║                                            ║
║   ██████╗  ██████╗ ██╗  ██╗ █████╗ ██╗    ║
║   ██╔══██╗██╔═══██╗██║ ██╔╝██╔══██╗██║    ║
║   ██████╔╝██║   ██║█████╔╝ ███████║██║    ║
║   ██╔══██╗██║   ██║██╔═██╗ ██╔══██║██║    ║
║   ██║  ██║╚██████╔╝██║  ██╗██║  ██║██║    ║
║   ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝    ║
║                                            ║
║   The Player. Linux-first. System v2.0    ║
║   Sung Jin-Woo Edition                     ║
║                                            ║
╚════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

log_info() {
    echo -e "${BLUE}[*]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[!]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

check_python() {
    log_info "Checking Python installation..."

    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 not found. Please install Python 3.10+"
        exit 1
    fi

    PY_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    PY_MAJOR=$(echo $PY_VERSION | cut -d. -f1)
    PY_MINOR=$(echo $PY_VERSION | cut -d. -f2)

    if [ "$PY_MAJOR" -lt 3 ] || ([ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]); then
        log_error "Python 3.10+ required. Found: $PY_VERSION"
        exit 1
    fi

    log_success "Python $PY_VERSION"
}

create_venv() {
    log_info "Creating Python virtual environment..."

    if [ "$INSTALL_TYPE" = "system" ]; then
        VENV_PATH="/opt/rokan/venv"
    else
        VENV_PATH="$HOME/.local/opt/rokan/venv"
    fi

    mkdir -p "$(dirname "$VENV_PATH")"

    if [ ! -d "$VENV_PATH" ]; then
        python3 -m venv "$VENV_PATH"
        log_success "Virtual environment created: $VENV_PATH"
    else
        log_warn "Virtual environment already exists"
    fi

    # Export for later use
    export VENV_PATH
}

install_dependencies() {
    log_info "Installing Python dependencies..."

    if [ -z "$VENV_PATH" ]; then
        if [ "$INSTALL_TYPE" = "system" ]; then
            VENV_PATH="/opt/rokan/venv"
        else
            VENV_PATH="$HOME/.local/opt/rokan/venv"
        fi
    fi

    source "$VENV_PATH/bin/activate"
    pip install --upgrade pip setuptools wheel
    pip install -q -r "$SCRIPT_DIR/requirements.txt"

    log_success "Dependencies installed"
}

install_rokan() {
    log_info "Installing Rokan package..."

    if [ -z "$VENV_PATH" ]; then
        if [ "$INSTALL_TYPE" = "system" ]; then
            VENV_PATH="/opt/rokan/venv"
        else
            VENV_PATH="$HOME/.local/opt/rokan/venv"
        fi
    fi

    source "$VENV_PATH/bin/activate"
    cd "$SCRIPT_DIR"
    pip install -e .

    log_success "Rokan package installed"
}

create_launcher_script() {
    log_info "Creating launcher script..."

    if [ "$INSTALL_TYPE" = "system" ]; then
        BIN_DIR="/usr/local/bin"
        VENV_PATH="/opt/rokan/venv"
    else
        BIN_DIR="$HOME/.local/bin"
        VENV_PATH="$HOME/.local/opt/rokan/venv"
    fi

    mkdir -p "$BIN_DIR"

    cat > "$BIN_DIR/rokan" << EOF
#!/bin/bash
# Rokan launcher script
source "$VENV_PATH/bin/activate"
exec python -m rokan_cli.main "\$@"
EOF

    chmod +x "$BIN_DIR/rokan"

    if [ "$INSTALL_TYPE" = "system" ]; then
        log_success "Launcher installed: /usr/local/bin/rokan"
        echo "export PATH=/usr/local/bin:\$PATH" >> /etc/profile.d/rokan.sh 2>/dev/null || true
    else
        log_success "Launcher installed: $HOME/.local/bin/rokan"
        if ! echo "$PATH" | grep -q "$HOME/.local/bin"; then
            log_warn "Add this to your ~/.bashrc or ~/.zshrc:"
            echo "export PATH=\"\$HOME/.local/bin:\$PATH\""
        fi
    fi
}

create_directories() {
    log_info "Creating data directories..."

    mkdir -p "$HOME/.rokan"/{logs,cache,data}
    mkdir -p "$HOME/.config/rokan"

    log_success "Directories created in ~/.rokan"
}

create_desktop_launcher() {
    log_info "Creating desktop launcher..."

    if [ "$INSTALL_TYPE" = "system" ]; then
        VENV_PATH="/opt/rokan/venv"
        DESKTOP_DIR="/usr/share/applications"
    else
        VENV_PATH="$HOME/.local/opt/rokan/venv"
        DESKTOP_DIR="$HOME/.local/share/applications"
    fi

    mkdir -p "$DESKTOP_DIR"

    cat > "$DESKTOP_DIR/rokan.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Rokan
Comment=The Player - AI System Assistant
Exec=bash -c 'source $VENV_PATH/bin/activate && python -m rokan_tui.app'
Icon=terminal
Terminal=true
Categories=Development;Utility;
Keywords=AI;CLI;Assistant;
EOF

    chmod 644 "$DESKTOP_DIR/rokan.desktop"

    if [ "$INSTALL_TYPE" = "system" ]; then
        log_success "Desktop launcher installed: /usr/share/applications/rokan.desktop"
    else
        log_success "Desktop launcher installed: $DESKTOP_DIR/rokan.desktop"
    fi
}

create_systemd_service() {
    log_info "Creating systemd user service..."

    if [ "$INSTALL_TYPE" = "system" ]; then
        VENV_PATH="/opt/rokan/venv"
        SERVICE_DIR="/etc/systemd/system"
    else
        VENV_PATH="$HOME/.local/opt/rokan/venv"
        SERVICE_DIR="$HOME/.config/systemd/user"
    fi

    mkdir -p "$SERVICE_DIR"

    cat > "$SERVICE_DIR/rokan.service" << EOF
[Unit]
Description=Rokan - The Player AI System
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$HOME
Environment="PATH=$VENV_PATH/bin:\$PATH"
ExecStart=$VENV_PATH/bin/python -m rokan_cli.main tui
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF

    chmod 644 "$SERVICE_DIR/rokan.service"

    if [ "$INSTALL_TYPE" = "system" ]; then
        log_success "Systemd service installed: /etc/systemd/system/rokan.service"
        log_info "Enable with: sudo systemctl enable rokan"
        log_info "Start with: sudo systemctl start rokan"
    else
        log_success "Systemd user service installed: $SERVICE_DIR/rokan.service"
        log_info "Enable with: systemctl --user enable rokan"
        log_info "Start with: systemctl --user start rokan"
        systemctl --user daemon-reload 2>/dev/null || true
    fi
}

print_summary() {
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║          ROKAN INSTALLATION COMPLETE                  ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════╝${NC}"
    echo ""

    if [ "$INSTALL_TYPE" = "system" ]; then
        echo -e "${CYAN}System-wide Installation${NC}"
        echo -e "  Install Type:  ${YELLOW}System${NC}"
        echo -e "  Binary:        ${YELLOW}/usr/local/bin/rokan${NC}"
        echo -e "  Venv:          ${YELLOW}/opt/rokan/venv${NC}"
        echo -e "  Service:       ${YELLOW}/etc/systemd/system/rokan.service${NC}"
    else
        echo -e "${CYAN}User Installation${NC}"
        echo -e "  Install Type:  ${YELLOW}User${NC}"
        echo -e "  Binary:        ${YELLOW}$HOME/.local/bin/rokan${NC}"
        echo -e "  Venv:          ${YELLOW}$HOME/.local/opt/rokan/venv${NC}"
        echo -e "  Service:       ${YELLOW}$HOME/.config/systemd/user/rokan.service${NC}"
    fi

    echo ""
    echo -e "${BLUE}Quick Start:${NC}"
    echo -e "  ${YELLOW}rokan${NC}              Launch the TUI"
    echo -e "  ${YELLOW}rokan ask${NC}          Ask a question"
    echo -e "  ${YELLOW}rokan models${NC}       Show available models"
    echo -e "  ${YELLOW}rokan status${NC}       System status"
    echo ""

    if [ "$INSTALL_TYPE" = "system" ]; then
        echo -e "${BLUE}Admin Commands:${NC}"
        echo -e "  ${YELLOW}sudo systemctl enable rokan${NC}   Enable at boot"
        echo -e "  ${YELLOW}sudo systemctl start rokan${NC}    Start daemon"
        echo -e "  ${YELLOW}sudo systemctl status rokan${NC}   Check status"
    else
        echo -e "${BLUE}User Commands:${NC}"
        if ! echo "$PATH" | grep -q "$HOME/.local/bin"; then
            echo -e "  ${YELLOW}export PATH=\$HOME/.local/bin:\$PATH${NC}"
            echo -e "  ${YELLOW}systemctl --user enable rokan${NC}"
            echo -e "  ${YELLOW}systemctl --user start rokan${NC}"
        else
            echo -e "  ${YELLOW}systemctl --user enable rokan${NC}   Enable at boot"
            echo -e "  ${YELLOW}systemctl --user start rokan${NC}    Start daemon"
        fi
    fi

    echo ""
    echo -e "${CYAN}Configuration:${NC}"
    echo -e "  ${YELLOW}~/.rokan/{{logs,cache,data}}${NC}     Data directories"
    echo -e "  ${YELLOW}~/.config/rokan{{NC}}                 Config directory"
    echo ""
    echo -e "${GREEN}Rokan is ready. Execute.${NC}"
}

main() {
    print_banner

    if [ "$INSTALL_TYPE" = "system" ] && [ "$EUID" -ne 0 ]; then
        log_error "System-wide installation requires sudo. Run:"
        echo "  sudo ./$0 system"
        exit 1
    fi

    log_info "Starting Rokan installation ($INSTALL_TYPE mode)"
    log_info "Source directory: $SCRIPT_DIR"

    check_python
    create_venv
    install_dependencies
    install_rokan
    create_launcher_script
    create_directories
    create_desktop_launcher
    create_systemd_service

    print_summary
}

# Run main
main "$@"
