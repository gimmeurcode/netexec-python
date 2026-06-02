#!/usr/bin/env bash
# install.command — NETEXEC macOS Installer
#
# Double-click this file from Finder.
# macOS opens a Terminal window automatically, runs the install, then closes it.
# No interaction required from the user.
#
# SCRIPT_DIR = netexec-mac/
# Go up one level to reach the repo root, then into the target folder.

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

echo "[1/4]  Building NETEXEC.app from latest source..."
if [ -f "$BUILD_SCRIPT" ]; then
    python3 "$BUILD_SCRIPT" || python "$BUILD_SCRIPT"
    echo "  Build complete."
else
    echo "  WARNING: build_game.py not found -- using existing NETEXEC.app."
    echo "  Expected: $BUILD_SCRIPT"
fi
echo ""

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
[ -d "$APP_DEST" ] && rm -rf "$APP_DEST"
cp -R "$APP_SRC" "$APP_DEST"
echo "  App installed to /Applications/NETEXEC.app"

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
