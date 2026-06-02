#!/usr/bin/env bash
# install.command -- NETEXEC macOS Installer launcher
#
# Double-click this file from Finder.
# macOS opens a Terminal window automatically, runs the install, then closes it.
# No interaction required from the user.

cd "$(dirname "$0")"
bash install_macos.sh
