#!/bin/bash
# Post-remove script for Rokan .deb package
# Removes the venv but keeps user data

echo "[ROKAN] Cleaning up..."
rm -rf "$HOME/.local/opt/rokan/venv" 2>/dev/null || true
echo "[ROKAN] Removed venv. Your data is still in ~/.rokan"
