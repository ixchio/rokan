#!/bin/bash
# ═══════════════════════════════════════════════════════════
# Build Rokan .deb package
# Run from the electron/ directory
# Output: dist/rokan_2.0.0_amd64.deb
# ═══════════════════════════════════════════════════════════

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "╔══════════════════════════════════════╗"
echo "║   Building Rokan .deb package        ║"
echo "╚══════════════════════════════════════╝"

# 1. Install Node dependencies
echo "[1/3] Installing dependencies..."
npm install

# 2. Copy renderer files (in case symlink doesn't work in build)
echo "[2/3] Preparing renderer..."
rm -rf renderer
mkdir -p renderer
cp ../rokan_gui/static/* renderer/

# 3. Build .deb
echo "[3/3] Building .deb..."
npx electron-builder --linux deb

echo ""
echo "════════════════════════════════════════"
echo "  Build complete!"
echo "  Output: $(ls dist/*.deb 2>/dev/null)"
echo ""
echo "  Install with:"
echo "    sudo dpkg -i dist/rokan_*.deb"
echo "    sudo apt-get install -f  # fix deps if needed"
echo "════════════════════════════════════════"
