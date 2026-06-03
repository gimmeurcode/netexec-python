"""
theme.py — NETEXEC Design System tokens (pygame build)

Mirrors assets/design-spec/style-spec.md.  All values match core/constants.py;
this module groups them by spec category, names the previously-hardcoded tint
surfaces, and owns font loading.

Usage
-----
UI code that only needs the C_* palette can keep importing from engine.constants.
UI code that needs tint surfaces, font loading, or structured token access should
import from here.

    from ui.theme import fonts, C_TINT_GREEN_FILL, SPACING, CRT
"""

from __future__ import annotations

import os
import sys
import pathlib
import pygame

# ── Re-export canonical colours from constants ─────────────────────────────────
from engine.constants import (
    # Phosphor
    C_GREEN_BRIGHT, C_GREEN_MID, C_GREEN_DIM, C_GREEN_PANEL, C_PANEL_ACCENT,
    # Plate / background
    C_BG, C_PANEL, C_PANEL_ALT, C_PANEL_BORDER,
    C_GREY_DARK, C_GREY_MID, C_GREY_LIGHT, C_WHITE,
    # Status (chrome)
    C_AMBER, C_AMBER_DIM, C_AMBER_GLOW,
    C_RED, C_RED_DIM, C_RED_GLOW,
    C_BLUE, C_BLUE_DIM, C_CYAN,
    C_SELECTED, C_HOVER, C_HOVER_PANEL, C_BORDER, C_BORDER_DIM,
    # Flash / scan
    C_FLASH_POS, C_FLASH_NEG, C_SCANLINE,
    # Net / projection
    C_NET_POS, C_NET_NEG, C_NET_NEUTRAL, C_VIEWS_ACCENT, C_INCOME_ACCENT,
    # Genre
    GENRE_COLORS,
    # Font size constants (kept in constants.py as single source)
    MIN_FONT_SIZE, FONT_TITLE, FONT_HEADER, FONT_BODY, FONT_SMALL, FONT_MICRO,
    # Spacing
    PAD,
)

# ── Tint surface colours ───────────────────────────────────────────────────────
# Very-dark RGB fill colours used as card/badge/button backgrounds.
# Named by purpose so callers don't scatter magic tuples across the codebase.

# Green tints
C_TINT_GREEN_VIVID   = (  0,  55,  18)  # AIR SEASON button fill (vivid press)
C_TINT_GREEN_FILL    = (  0,  38,  12)  # selected card bg / contract accept btn
C_TINT_GREEN_TAB     = (  0,  32,  10)  # active shop tab bg
C_TINT_GREEN_HOVER   = (  0,  50,  22)  # upgrade tile hover bg
C_TINT_GREEN_TILE    = (  0,  28,  10)  # upgrade tile normal bg
C_TINT_GREEN_BADGE   = (  0,  30,  12)  # green badge / on-track pill bg
C_TINT_GREEN_DEEP    = (  0,  25,   5)  # slot card "selected-item" bg
C_TINT_GREEN_SEL     = (  0,  28,  14)  # wildcard-show selected card bg
C_TINT_GREEN_NOTCH   = (  0,  20,   8)  # wildcard-show step notch bg
C_TINT_GREEN_PILL    = (  0,  14,   6)  # ad SIGN pill bg (can buy)

# Show pill
C_TINT_SHOW_PILL     = ( 14,  24,  10)  # show BUY pill bg (can buy)

# Teal tint
C_TINT_TEAL_BADGE    = (  0,  30,  40)  # vault-rerun "FROZEN" badge bg

# Red tints
C_TINT_RED_BADGE     = ( 30,   5,   5)  # short-by / off-track pill bg
C_TINT_RED_DARK      = ( 20,  10,  10)  # insufficient-budget card bg / loan box
C_TINT_RED_PILL      = ( 24,   6,   6)  # "INSUFFICIENT FUNDS" overlay bg

# Blue tint
C_TINT_BLUE_DARK     = ( 10,  10,  22)  # grant box bg

# Amber tints
C_TINT_AMBER_SEL     = ( 28,  20,   0)  # wildcard-ad selected card bg
C_TINT_AMBER_NOTCH   = ( 10,  10,   0)  # wildcard-ad step notch bg
C_TINT_AMBER_FALLBACK= ( 30,  20,   0)  # GENRE_COLORS fallback plate (ad wildcard)

# Neutral
C_TINT_SHADOW        = (  0,   0,   0)  # drop shadow / hard black

# Shared widget tints
C_TINT_BTN_HOVER     = (  0,  58,  18)  # button default hover fill
C_TINT_PANEL_TITLE   = (  0,  28,   8)  # draw_panel_box title bar fill

# ── Time slot high-contrast identity colors ────────────────────────────────────
# Each slot has a distinct background tint and accent so players can tell them
# apart at a glance.  Defined here to avoid magic tuples scattered across
# playing_schedule.py.  Index matches TIME_SLOTS order (Morning=0 … Late Night=3).

SLOT_COLORS: list[dict] = [
    {"bg": (40, 20,  0), "accent": (220, 140,   0)},  # Morning    — orange-gold
    {"bg": ( 0, 15, 40), "accent": (  0, 140, 220)},  # Afternoon  — bright blue
    {"bg": (40,  0, 10), "accent": (220,   0,  60)},  # Prime Time — vivid red
    {"bg": (15,  0, 35), "accent": (120,   0, 200)},  # Late Night — purple
]

# ── Shop tab identity colors ───────────────────────────────────────────────────
# One unique accent per tab.  Active tab renders at full strength; inactive tabs
# dim to 40% so the active tab pops clearly.

TAB_COLORS: dict[str, tuple] = {
    "shows":     (  0, 180, 180),  # teal
    "stars":     (220, 180,   0),  # gold
    "ads":       (220, 100,   0),  # orange
    "upgrades":  (  0, 200,  80),  # green
    "events":    (200,   0, 100),  # magenta
    "contracts": (120,   0, 220),  # violet
}

# ── Typography ramp ────────────────────────────────────────────────────────────
# Role → (size_pt, bold).  Sizes mirror FONT_* in constants.py.

FONT_ROLES: dict[str, tuple[int, bool]] = {
    "title":  (FONT_TITLE,  True),   # 34 bold — main menu / game-over title
    "header": (FONT_HEADER, True),   # 22 bold — panel headers, season counter
    "body":   (FONT_BODY,   False),  # 18 — card text, labels
    "bold":   (FONT_BODY,   True),   # 18 bold — card names, HUD values
    "small":  (FONT_SMALL,  False),  # 16 — sub-labels, genre badges
    "micro":  (FONT_MICRO,  False),  # 15 — tooltips, fine-print numbers
}

# ── Spacing scale ──────────────────────────────────────────────────────────────

SPACING = {
    "xs":  4,
    "sm":  8,
    "md":  12,
    "lg":  16,
    "xl":  24,
    "pad": PAD,   # universal internal pad = 6
}

# ── Shape tokens ──────────────────────────────────────────────────────────────

RADIUS = {
    "chip":   3,   # badges / chips / buttons
    "card":   4,   # panels / cards
    "modal":  8,   # modal dialogs
}

# ── CRT parameters ─────────────────────────────────────────────────────────────

CRT = {
    "scanline_spacing": 3,       # px between scanline strips
    "scanline_alpha":   0.16,    # strip opacity (0–1); game uses 22/255 ≈ 0.086
    "shadow_mask_cells": 3,      # px cell width for vertical shadow-mask
    "shadow_mask_alpha": 0.11,   # faint pixel-grid opacity
    "glow_radius":       8,      # px — bright text bloom only
    "vignette":          0.68,   # corner darkening coefficient (0–1)
    "curvature":         0.018,  # bezel rounding suggestion — not a glyph filter
    "chroma_aberration": 0.5,    # px hard cap; never split glyph channels
    "flicker":           False,  # text flicker disabled; chrome LEDs only
}

# ── Font loading ───────────────────────────────────────────────────────────────

def load_fonts() -> dict[str, pygame.font.Font]:
    """
    Return a dict of pygame font objects keyed by role name.

    Resolves paths correctly for both local development and PyInstaller bundled 
    executables (using sys._MEIPASS). Tries bundled TTF files first, then 
    falls back to preferred system monospace fonts.
    """
    pygame.font.init()
    
    # 1. Determine base path (Handles both Dev and PyInstaller Exe)
    try:
        # PyInstaller extracts bundled data here at runtime
        base_path = pathlib.Path(sys._MEIPASS)
    except AttributeError:
        # Standard local dev run
        base_path = pathlib.Path(__file__).resolve().parent.parent

    # Point to the exact assets/fonts folder you created
    assets_dir = base_path / "assets" / "fonts"

    def _try_ttf(name: str, size: int, bold: bool) -> pygame.font.Font | None:
        # Maps "IBMPlexMono" and True/False to your exact filenames:
        # - IBMPlexMono-Bold.ttf
        # - IBMPlexMono-Regular.ttf
        suffixes = ["-Bold.ttf", "-Regular.ttf", ".ttf"] if bold else ["-Regular.ttf", ".ttf"]
        
        for suf in suffixes:
            p = assets_dir / (name + suf)
            if p.exists():
                try:
                    return pygame.font.Font(str(p), size)
                except Exception as e:
                    print(f"Warning: Found {p.name} but failed to load it: {e}")
                    pass
        return None

    def _sysfont(size: int, bold: bool) -> pygame.font.Font:
        preferred = [
            "ibmplexmono", "ibm plex mono",
            "consolas", "cascadiamono", "jetbrainsmono",
            "couriernew", "courier new", "courier", "monospace",
        ]
        for name in preferred:
            try:
                f = pygame.font.SysFont(name, size, bold=bold)
                if f:
                    return f
            except Exception:
                continue
        # Ultimate fallback if everything else fails
        return pygame.font.Font(None, size)

    result: dict[str, pygame.font.Font] = {}
    
    for role, (size, bold) in FONT_ROLES.items():
        size = max(size, MIN_FONT_SIZE)
        
        # Look for Saira first (for headers), then IBMPlexMono, then System Font fallback
        f = (
            _try_ttf("Saira", size, bold) if role in ("title", "header") else None
        ) or _try_ttf("IBMPlexMono", size, bold) or _sysfont(size, bold)
        
        result[role] = f
        
    return result