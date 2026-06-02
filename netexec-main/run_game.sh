#!/bin/bash
# run_game.sh — NETEXEC launcher for macOS / Linux
# Double-click or run: bash run_game.sh
cd "$(dirname "$0")"
python3 main.py 2>/dev/null || python main.py
if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Could not launch NETEXEC."
    echo "Make sure Python 3 and pygame are installed."
    echo ""
    echo "Install pygame with:"
    echo "    pip3 install pygame"
    echo ""
fi
