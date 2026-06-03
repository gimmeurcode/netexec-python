#!/usr/bin/env bash
# install.command — NETEXEC macOS Installer
#
# Double-click this file from Finder.
# macOS opens a Terminal window automatically, runs the install, then closes it.
# No interaction required from the user.
#
# SCRIPT_DIR = installers/macos/ — two levels deep, so repo root is ../..

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_SCRIPT="$SCRIPT_DIR/../../dev/build/build_game.py"
APP_SRC="$SCRIPT_DIR/../../dist/NETEXEC.app"
APP_DEST="/Applications/NETEXEC.app"
DESKTOP_LINK="$HOME/Desktop/NetExecutive.app"

echo "=============================================================="
echo "  NETEXEC -- macOS Application Installer"
echo "=============================================================="
echo ""

echo "[1/4]  Building NETEXEC.app from latest source..."
# If build_game.py is present, always rebuild so the install is up-to-date.
# If it is absent (player zip), use the pre-built NETEXEC.app in netexec-main/.
if [ -f "$BUILD_SCRIPT" ]; then
    python3 "$BUILD_SCRIPT" || python "$BUILD_SCRIPT"
    echo "  Build complete."
else
    echo "  build_game.py not found -- using existing NETEXEC.app (zip distribution)."
    if [ ! -d "$APP_SRC" ]; then
        echo "ERROR: NETEXEC.app not found at $APP_SRC"
        echo "Expected pre-built app or build script at: $BUILD_SCRIPT"
        echo ""
        exit 1
    fi
fi
echo ""

if [ ! -d "$APP_SRC" ]; then
    echo "ERROR: NETEXEC.app not found at $APP_SRC"
    echo "Make sure dist/ and netexec-mac/ are in the same parent folder."
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
echo "[3/4]  Preserving user saves and settings..."
USER_SETTINGS="$HOME/.config/NETEXEC"
if [ -d "$USER_SETTINGS" ]; then
    echo "  Existing saves kept at: $USER_SETTINGS"
else
    echo "  No previous saves found — first install."
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
echo "  App   : /Applications/NETEXEC.app"
echo "  Saves : ~/.config/NETEXEC/"
echo ""
# Offer to launch the game immediately
open "/Applications/NETEXEC.app"
echo "  Game launched."
echo "=============================================================="
echo ""
