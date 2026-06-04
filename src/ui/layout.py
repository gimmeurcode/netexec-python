"""
layout.py — NETEXEC responsive layout engine
=============================================
Given a (width, height) pair, computes every named screen region as a
pygame.Rect so no screen module hard-codes pixel coordinates.

Usage
-----
    from ui.layout import compute_layout, MIN_W, MIN_H

    layout = compute_layout(sw, sh)
    pygame.draw.rect(surface, color, layout.hud)
    pygame.draw.rect(surface, color, layout.schedule)
    slot_rect = pygame.Rect(x, y, layout.schedule.width, layout.slot_h)

Proportions
-----------
All fractions are derived from the original fixed constants in constants.py
so the game looks identical at 1280×800 (the design reference size).

Bezel
-----
The console bezel adds a chrome frame around the game area.  Game content
is rendered into a sub-surface (layout.cutout) so no screen module needs
to know about the rails.  The cutout rect is in window coordinates; all
other rects are relative to the cutout origin (0, 0).

BEZEL_RAIL_H  — pixel height of the top and bottom chrome rails.
BEZEL_PAD     — horizontal/inner padding between the window edge and the cutout.

Breakpoints
-----------
BREAKPOINT_STACK_W — window width below which the two columns would stack
vertically. The renderer does not yet implement stacking; this constant is
exposed so a future pass can act on it without hunting for the magic number.
"""

from __future__ import annotations
from dataclasses import dataclass
import pygame

# ── Minimum window dimensions ──────────────────────────────────────────────────
MIN_W = 800
MIN_H = 600

# Below this window width the two columns should stack vertically.
BREAKPOINT_STACK_W = 720

# ── Bezel geometry ─────────────────────────────────────────────────────────────
BEZEL_RAIL_H = 48   # top and bottom chrome rail height (px)
BEZEL_PAD    = 10   # left/right inset from window edge to cutout

# Universal padding — mirrors PAD in core/constants.py.
_PAD = 6

# Column split: left panel takes this fraction of window width.
# Matches the pre-existing formula  _L = int(sw * 0.502)  in GameUI.
_SPLIT = 0.502

# HUD height as a fraction of cutout height, clamped to [_HUD_MIN, _HUD_MAX].
# At 704 px cutout height (800 − 96 rails): 704 × 0.107 ≈ 75 px — matches HEADER_H.
_HUD_FRAC = 0.107
_HUD_MIN  = 68
_HUD_MAX  = 90

# Reference stage height (cutout 704 px − 75 HUD − 12 pad).
_REF_STAGE_H = 617


@dataclass(frozen=True)
class Layout:
    """
    All named screen regions for a given window size.

    Immutable: compute a fresh Layout on each render call (it's a cheap
    dataclass, not a heavy object) so callers never hold stale geometry.

    All rects *except* ``cutout`` are expressed in game-surface (cutout-local)
    coordinates starting at (0, 0).  The caller must blit the game surface at
    ``cutout.topleft`` to position it correctly in the window.
    """

    sw: int   # full window width
    sh: int   # full window height

    # Game sub-surface area in window coordinates
    cutout: pygame.Rect

    # HUD strip (full cutout width, top of game surface)
    hud_h: int
    hud:   pygame.Rect

    # Column extents (within game surface)
    left_w:  int
    right_w: int
    right_x: int

    # Full-height panel rects for each column (below HUD)
    schedule: pygame.Rect
    shop:     pygame.Rect

    # Component heights, scaled proportionally to available stage height
    slot_h:           int
    vault_h:          int
    upgrade_row_h:    int
    monopoly_bar_h:   int
    seasonal_strip_h: int
    shop_card_h:      int
    tab_row_h:        int
    reroll_h:         int

    # Centered overlay area (largest comfortable modal region, cutout-local)
    modal: pygame.Rect


def compute_layout(sw: int, sh: int) -> Layout:
    """
    Compute all screen regions for a window of (sw, sh) pixels.

    Values are clamped so nothing collapses below legibility even when the
    window is dragged to the minimum supported size (MIN_W × MIN_H).
    """
    sw = max(sw, MIN_W)
    sh = max(sh, MIN_H)

    # ── Bezel cutout — game content lives inside this rect ─────────────────────
    cut_x = BEZEL_PAD
    cut_y = BEZEL_RAIL_H
    cut_w = max(MIN_W - BEZEL_PAD * 2, sw - BEZEL_PAD * 2)
    cut_h = max(MIN_H - BEZEL_RAIL_H * 2, sh - BEZEL_RAIL_H * 2)
    cutout = pygame.Rect(cut_x, cut_y, cut_w, cut_h)

    # From here all values are relative to the game surface (cutout origin = 0,0)
    cw, ch = cut_w, cut_h

    # HUD
    hud_h = max(_HUD_MIN, min(_HUD_MAX, int(ch * _HUD_FRAC)))
    hud   = pygame.Rect(0, 0, cw, hud_h)

    # Two-column split
    left_w  = max(380, int(cw * _SPLIT))
    right_w = max(380, cw - left_w - _PAD)
    right_x = left_w + _PAD

    # Stage area (everything below the HUD)
    stage_y = hud_h + _PAD
    stage_h = max(1, ch - stage_y - _PAD)

    # Panel rects
    schedule = pygame.Rect(_PAD,           stage_y, left_w  - _PAD * 2, stage_h)
    shop     = pygame.Rect(right_x + _PAD, stage_y, right_w - _PAD * 2, stage_h)

    # Scale component heights proportionally to stage height
    scale = stage_h / _REF_STAGE_H

    slot_h           = max(80, int(120 * scale))
    vault_h          = max(70, int(102 * scale))
    upgrade_row_h    = max(40, int( 56 * scale))
    monopoly_bar_h   = max(20, int( 28 * scale))
    seasonal_strip_h = max(36, int( 52 * scale))
    shop_card_h      = max(90, int(132 * scale))
    tab_row_h        = max(36, int( 48 * scale))
    reroll_h         = max(36, int( 50 * scale))

    # Modal overlay: 82% of cutout width, 88% of stage height, centered
    mw    = max(400, int(cw      * 0.82))
    mh    = max(300, int(stage_h * 0.88))
    modal = pygame.Rect(
        (cw - mw) // 2,
        stage_y + (stage_h - mh) // 2,
        mw, mh,
    )

    return Layout(
        sw=sw, sh=sh,
        cutout=cutout,
        hud_h=hud_h, hud=hud,
        left_w=left_w, right_w=right_w, right_x=right_x,
        schedule=schedule, shop=shop,
        slot_h=slot_h, vault_h=vault_h,
        upgrade_row_h=upgrade_row_h, monopoly_bar_h=monopoly_bar_h,
        seasonal_strip_h=seasonal_strip_h,
        shop_card_h=shop_card_h, tab_row_h=tab_row_h, reroll_h=reroll_h,
        modal=modal,
    )
