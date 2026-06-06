"""
version.py — NETEXEC: Network Executive Simulator
==================================================
Single source of truth for the game version.

All version strings come from here so that the build script, the in-game
About screen, and the release zip always report the same number.

Steam / Steamworks integration note
------------------------------------
When the game ships on Steam, replace VERSION with the value from the
Steamworks SDK build_id call — or keep VERSION as the marketing number
and add a separate BUILD_ID for Steamworks telemetry.

Usage
-----
    from version import VERSION, DISPLAY_NAME
    print(f"{DISPLAY_NAME} v{VERSION}")
"""

# Semantic version: MAJOR.MINOR.PATCH
# Bump PATCH for bug-fix-only builds.
# Bump MINOR for new features / balance passes.
# Bump MAJOR for full reboots or breaking save-format changes.
VERSION = "1.1.0"

# Human-readable title used in window title, About screen, etc.
DISPLAY_NAME = "NETEXEC: Network Executive Simulator"

# Short build tag — override via CI env var in automated pipelines.
# Format: "vMAJOR.MINOR.PATCH"
BUILD_TAG = f"v{VERSION}"
