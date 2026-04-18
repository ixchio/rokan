#!/bin/bash
# Post-install script for Rokan .deb package
# Sets up the Python venv and data directory

set -e

ROKAN_DIR="/opt/Rokan/resources/python"
DATA_DIR="$HOME/.rokan"
VENV_DIR="$HOME/.local/opt/rokan/venv"

echo "[ROKAN] Setting up Python environment..."

# Create data directory
mkdir -p "$DATA_DIR"

# Create .env template if missing
if [ ! -f "$DATA_DIR/.env" ]; then
    cat > "$DATA_DIR/.env" << 'ENV'
# Rokan — API Keys
# Get a free key at https://build.nvidia.com
NVIDIA_API_KEY=
ENV
    echo "[ROKAN] Created $DATA_DIR/.env — add your NVIDIA_API_KEY there"
fi

# Create venv
if [ ! -d "$VENV_DIR" ]; then
    mkdir -p "$(dirname "$VENV_DIR")"
    python3 -m venv --system-site-packages "$VENV_DIR"
    "$VENV_DIR/bin/pip" install --upgrade pip -q
    if [ -d "$ROKAN_DIR" ]; then
        "$VENV_DIR/bin/pip" install -e "$ROKAN_DIR" -q
    fi
    "$VENV_DIR/bin/pip" install duckduckgo-search -q 2>/dev/null || true
    echo "[ROKAN] Python venv ready: $VENV_DIR"
fi

echo "[ROKAN] Installation complete. Set your API key:"
echo "  nano ~/.rokan/.env"
