#!/usr/bin/env bash
# install_macos.sh -- NETEXEC macOS Application Installer
#
# Double-click install.command (in Finder) or run from Terminal:
#   bash install_macos.sh
#
# What this installer does:
#   1. Builds NETEXEC.app from source (requires Python 3 + pygame)
#   2. Copies NETEXEC.app to /Applications/
#   3. Creates a Desktop shortcut
#   4. Backs up any existing user settings
#
# SCRIPT_DIR = netexec-mac/
# Go up one level to reach the game root, then into the target folder.
#
# Terminal opens automatically and closes when done -- no interaction needed.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_SCRIPT="$SCRIPT_DIR/../netexec-dev/build/build_game.py"
APP_SRC="$SCRIPT_DIR/../netexec-main/NETEXEC.app"
APP_DEST="/Applications/NETEXEC.app"
DESKTOP_LINK="$HOME/Desktop/NetExecutive.app"

echo "=============================================================="
echo "  NETEXEC -- macOS Application Installer"
echo "=============================================================="
echo ""

# Build NETEXEC.app from latest source before installing
echo "[1/4]  Building NETEXEC.app from latest source..."
if [ -f "$BUILD_SCRIPT" ]; then
    python3 "$BUILD_SCRIPT" || python "$BUILD_SCRIPT"
    echo "  Build complete."
else
    echo "  WARNING: build_game.py not found -- using existing NETEXEC.app."
    echo "  Expected: $BUILD_SCRIPT"
fi
echo ""

# Verify the source app bundle exists
if [ ! -d "$APP_SRC" ]; then
    echo "ERROR: NETEXEC.app not found at $APP_SRC"
    echo "Make sure netexec-main/ and netexec-mac/ are in the same parent folder."
    echo ""
    exit 1
fi

echo "[2/4]  Installing NETEXEC.app to /Applications..."
echo "  Source      : $APP_SRC"
echo "  Destination : $APP_DEST"
echo ""

# Remove previous install
if [ -d "$APP_DEST" ]; then
    echo "  Removing previous install..."
    rm -rf "$APP_DEST"
fi

cp -R "$APP_SRC" "$APP_DEST"
echo "  App installed to /Applications/NETEXEC.app"

# Back up and clear old user settings so new defaults apply
echo ""
echo "[3/4]  Backing up and clearing old user settings..."
USER_SETTINGS="$HOME/.config/NETEXEC"
if [ -d "$USER_SETTINGS" ]; then
    TS="$(date +%Y%m%d-%H%M%S)"
    BACKUP="$HOME/.config/NETEXEC-settings-backup-$TS"
    cp -R "$USER_SETTINGS" "$BACKUP"
    rm -rf "$USER_SETTINGS"
    echo "  Settings backed up to: $BACKUP"
    echo "  Old settings cleared. Game will start with fresh defaults."
else
    echo "  No previous settings found."
fi

# Create Desktop alias/symlink
echo ""
echo "[4/4]  Creating Desktop shortcut..."
DESKTOP="$HOME/Desktop"

if [ ! -d "$DESKTOP" ]; then
    echo "  No Desktop directory found -- shortcut skipped."
else
    if [ -e "$DESKTOP_LINK" ] || [ -L "$DESKTOP_LINK" ]; then
        rm -f "$DESKTOP_LINK"
    fi
    ln -sf "$APP_DEST" "$DESKTOP_LINK"
    echo "  Desktop shortcut  : $DESKTOP_LINK -> $APP_DEST"
fi

echo ""
echo "  Installation complete!"
echo "  Launch NetExecutive from Applications or your Desktop."
echo "  App       : /Applications/NETEXEC.app"
echo "  Saves     : ~/.config/NETEXEC/"
echo "=============================================================="
echo ""
# No pause -- terminal closes automatically when the script finishes.
