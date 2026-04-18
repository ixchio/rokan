#!/bin/bash
# Rokan Uninstall Script
# Safely removes Rokan from the system

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

INSTALL_TYPE="${1:-user}"  # user or system

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

confirm() {
    local prompt="$1"
    local response
    read -p "$(echo -e ${YELLOW})$prompt (y/N): $(echo -e ${NC})" response
    [[ "$response" =~ ^[Yy]$ ]]
}

if [ "$INSTALL_TYPE" = "system" ] && [ "$EUID" -ne 0 ]; then
    log_error "System-wide uninstallation requires sudo. Run:"
    echo "  sudo ./$0 system"
    exit 1
fi

echo -e "${RED}"
cat << "EOF"
╔════════════════════════════════════════════╗
║                                            ║
║         ROKAN UNINSTALL UTILITY            ║
║                                            ║
╚════════════════════════════════════════════╝
EOF
echo -e "${NC}"

log_info "Uninstalling Rokan ($INSTALL_TYPE mode)"
echo ""

# Stop services if running
if [ "$INSTALL_TYPE" = "system" ]; then
    if systemctl is-active --quiet rokan; then
        log_info "Stopping rokan service..."
        sudo systemctl stop rokan || true
        sudo systemctl disable rokan || true
    fi

    SERVICE_FILE="/etc/systemd/system/rokan.service"
    BIN_FILE="/usr/local/bin/rokan"
    DESKTOP_FILE="/usr/share/applications/rokan.desktop"
    VENV_PATH="/opt/rokan/venv"
else
    if systemctl --user is-active --quiet rokan 2>/dev/null; then
        log_info "Stopping rokan user service..."
        systemctl --user stop rokan || true
        systemctl --user disable rokan || true
    fi

    SERVICE_FILE="$HOME/.config/systemd/user/rokan.service"
    BIN_FILE="$HOME/.local/bin/rokan"
    DESKTOP_FILE="$HOME/.local/share/applications/rokan.desktop"
    VENV_PATH="$HOME/.local/opt/rokan/venv"
fi

echo ""
log_info "Files to remove:"
echo "  - $SERVICE_FILE"
echo "  - $BIN_FILE"
echo "  - $DESKTOP_FILE"
echo "  - $VENV_PATH"
echo "  - $HOME/.rokan (data directory)"
echo ""

if confirm "Continue with uninstallation?"; then
    log_info "Removing files..."

    # Remove service file
    if [ -f "$SERVICE_FILE" ]; then
        rm -f "$SERVICE_FILE"
        log_success "Removed service file"
    fi

    # Remove binary
    if [ -f "$BIN_FILE" ]; then
        rm -f "$BIN_FILE"
        log_success "Removed launcher binary"
    fi

    # Remove desktop file
    if [ -f "$DESKTOP_FILE" ]; then
        rm -f "$DESKTOP_FILE"
        log_success "Removed desktop launcher"
    fi

    # Remove virtual environment
    if [ -d "$VENV_PATH" ]; then
        rm -rf "$VENV_PATH"
        log_success "Removed virtual environment"
    fi

    # Ask about data
    echo ""
    if confirm "Remove data directory ($HOME/.rokan)?"; then
        rm -rf "$HOME/.rokan"
        log_success "Removed data directory"
    else
        log_warn "Kept data directory at $HOME/.rokan"
    fi

    if [ "$INSTALL_TYPE" = "user" ]; then
        systemctl --user daemon-reload 2>/dev/null || true
    fi

    echo ""
    echo -e "${GREEN}✓ Rokan has been uninstalled${NC}"
else
    echo -e "${YELLOW}Uninstallation cancelled${NC}"
    exit 0
fi
