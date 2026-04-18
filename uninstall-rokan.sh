#!/bin/bash
# Rokan — Uninstaller
# Removes the desktop app, venv, launcher, service.
# Does NOT delete ~/.rokan (your data/memories) unless you pass --purge.

R='\033[0;31m' G='\033[0;32m' Y='\033[1;33m' B='\033[0;34m' N='\033[0m'
ok()   { echo -e "${G}[✓]${N} $1"; }
info() { echo -e "${B}[*]${N} $1"; }
warn() { echo -e "${Y}[!]${N} $1"; }

PURGE=false
[ "$1" = "--purge" ] && PURGE=true

echo -e "${R}"
echo "  Uninstalling Rokan..."
echo -e "${N}"

# Stop service
systemctl --user stop rokan 2>/dev/null
systemctl --user disable rokan 2>/dev/null
sudo systemctl stop rokan 2>/dev/null
sudo systemctl disable rokan 2>/dev/null

# Remove files
rm -f "$HOME/.local/bin/rokan" && ok "Removed launcher"
rm -f "/usr/local/bin/rokan" 2>/dev/null
rm -f "$HOME/.local/share/applications/rokan.desktop" && ok "Removed desktop entry"
rm -f "/usr/share/applications/rokan.desktop" 2>/dev/null
rm -f "$HOME/.config/systemd/user/rokan.service" && ok "Removed service"
rm -f "/etc/systemd/system/rokan.service" 2>/dev/null
rm -rf "$HOME/.local/opt/rokan" && ok "Removed venv"
rm -rf "/opt/rokan" 2>/dev/null
rm -rf "$HOME/.local/share/icons/hicolor/256x256/apps/rokan.svg" 2>/dev/null

# Reload systemd
systemctl --user daemon-reload 2>/dev/null

if [ "$PURGE" = true ]; then
    warn "Purging all data (memories, config)..."
    rm -rf "$HOME/.rokan"
    rm -rf "$HOME/.config/rokan"
    ok "Data purged"
else
    info "Kept your data in ~/.rokan (use --purge to delete)"
fi

echo ""
echo -e "${G}Rokan uninstalled.${N}"
