#!/bin/bash
# run_installer.sh — Terminal fallback launcher for install.command
#
# If macOS blocks install.command with "no appropriate access privileges",
# open Terminal and run:
#   bash run_installer.sh
#
# This script ensures install.command is marked executable, then runs it.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMMAND="$SCRIPT_DIR/install.command"

if [ ! -f "$COMMAND" ]; then
    echo "ERROR: install.command not found at $COMMAND"
    exit 1
fi

chmod +x "$COMMAND"
"$COMMAND"
