"""
bezel.py — NETEXEC console chrome frame
=========================================
Draws the brushed-metal console shell around the game screen cutout.

Layout (from design-spec/layout-map.md)
----------------------------------------
Top rail  (BEZEL_RAIL_H px):
  [screw]  [NETEXEC BC-12 nameplate]  [LED red][LED amber][LED green]  [screw]
Cutout:    game content rendered here by ui.py
Bottom rail (BEZEL_RAIL_H px):
  [screw]  [knob]  [VU label + bar]  [SIGNAL label]  [toggle]
  [ON-AIR status chip]

Chrome color tokens (from design-spec/style-spec.md, "Chrome metals" section):
  hi    #43474f   bright highlight
  base  #2a2d33   panel fill
  lo    #16181c   dark shadow
  groove#0c0d10   deepest groove
  inner #050507   bezel-inner / screen mask
  label #aeb4be   engraved text

The ON-AIR LED blinks at 700ms (matches the existing BLINK_PERIOD_MS = 700).
"""

from __future__ import annotations

import math
import pygame

from ui.layout import Layout, BEZEL_RAIL_H, BEZEL_PAD
from engine.constants import BLINK_PERIOD_MS, MIN_FONT_SIZE

# ── Chrome palette ─────────────────────────────────────────────────────────────
C_CHROME_HI     = (0x43, 0x47, 0x4f)
C_CHROME_BASE   = (0x2a, 0x2d, 0x33)
C_CHROME_LO     = (0x16, 0x18, 0x1c)
C_CHROME_GROOVE = (0x0c, 0x0d, 0x10)
C_BEZEL_INNER   = (0x05, 0x05, 0x07)
C_CHROME_LABEL  = (0xae, 0xb4, 0xbe)

# Status LED colours
C_LED_RED    = (0xff, 0x3c, 0x3c)
C_LED_AMBER  = (0xff, 0xbe, 0x14)
C_LED_GREEN  = (0x00, 0xff, 0x64)
C_LED_OFF    = (0x22, 0x22, 0x28)

# Glow alpha for active LEDs
_LED_GLOW_A = 55


def draw_bezel(surface: pygame.Surface, layout: Layout, tick_ms: int,
               on_air: bool = False) -> None:
    """
    Draw the full console chrome frame over the window surface.

    Parameters
    ----------
    surface   : main pygame display surface
    layout    : current Layout (provides cutout rect and window size)
    tick_ms   : running tick counter for LED blink animation
    on_air    : True while a season is actively airing (red ON-AIR LED blinks)
    """
    sw, sh = layout.sw, layout.sh
    cut    = layout.cutout

    # ── Outer shell fill (chrome base) ────────────────────────────────────────
    # Top rail
    top_rail = pygame.Rect(0, 0, sw, cut.top)
    pygame.draw.rect(surface, C_CHROME_BASE, top_rail)

    # Bottom rail
    bot_rail = pygame.Rect(0, cut.bottom, sw, sh - cut.bottom)
    pygame.draw.rect(surface, C_CHROME_BASE, bot_rail)

    # Left / right side strips
    pygame.draw.rect(surface, C_CHROME_BASE, pygame.Rect(0, cut.top, cut.left, cut.height))
    pygame.draw.rect(surface, C_CHROME_BASE,
                     pygame.Rect(cut.right, cut.top, sw - cut.right, cut.height))

    # ── Highlight / shadow bevels ──────────────────────────────────────────────
    # Top edge highlight
    pygame.draw.line(surface, C_CHROME_HI, (0, 0), (sw, 0), 2)
    # Bottom edge shadow
    pygame.draw.line(surface, C_CHROME_GROOVE, (0, sh - 1), (sw, sh - 1), 2)
    # Left edge
    pygame.draw.line(surface, C_CHROME_HI, (0, 0), (0, sh), 2)
    # Right edge
    pygame.draw.line(surface, C_CHROME_GROOVE, (sw - 1, 0), (sw - 1, sh), 2)

    # ── Screen cutout border ──────────────────────────────────────────────────
    # Inner shadow around cutout (makes screen appear recessed)
    inset = cut.inflate(4, 4)
    pygame.draw.rect(surface, C_CHROME_GROOVE, inset, 2, border_radius=2)
    pygame.draw.rect(surface, C_BEZEL_INNER,   cut,   2, border_radius=1)

    # ── Top rail contents ──────────────────────────────────────────────────────
    rail_cy = cut.top // 2           # vertical centre of top rail

    # Left screw
    _draw_screw(surface, BEZEL_PAD + 10, rail_cy)

    # Nameplate: NETEXEC BC-12
    _draw_nameplate(surface, BEZEL_PAD + 30, rail_cy, sw)

    # LEDs (right side, before right screw)
    led_x = sw - BEZEL_PAD - 30 - 60
    _draw_leds(surface, led_x, rail_cy, tick_ms, on_air)

    # Right screw
    _draw_screw(surface, sw - BEZEL_PAD - 10, rail_cy)

    # ── Bottom rail contents ───────────────────────────────────────────────────
    bot_cy = cut.bottom + (sh - cut.bottom) // 2

    # Left screw
    _draw_screw(surface, BEZEL_PAD + 10, bot_cy)

    # Knob
    _draw_knob(surface, BEZEL_PAD + 36, bot_cy)

    # VU meter with label
    _draw_vu_strip(surface, BEZEL_PAD + 68, bot_cy, sw, tick_ms)

    # Right screw
    _draw_screw(surface, sw - BEZEL_PAD - 10, bot_cy)


# ── Font cache ─────────────────────────────────────────────────────────────────

_BEZEL_FONTS: dict[tuple, pygame.font.Font] = {}


def _get_bezel_font(size: int, bold: bool = False) -> pygame.font.Font:
    key = (size, bold)
    if key not in _BEZEL_FONTS:
        _BEZEL_FONTS[key] = pygame.font.SysFont("consolas,monospace", size, bold=bold)
    return _BEZEL_FONTS[key]


# ── Chrome sub-elements ────────────────────────────────────────────────────────

def _draw_screw(surface: pygame.Surface, cx: int, cy: int) -> None:
    r = 5
    pygame.draw.circle(surface, C_CHROME_LO,  (cx, cy), r)
    pygame.draw.circle(surface, C_CHROME_HI,  (cx, cy), r, 1)
    # Phillips cross slots
    pygame.draw.line(surface, C_CHROME_GROOVE, (cx - 3, cy), (cx + 3, cy), 1)
    pygame.draw.line(surface, C_CHROME_GROOVE, (cx, cy - 3), (cx, cy + 3), 1)


def _draw_nameplate(surface: pygame.Surface, x: int, cy: int, sw: int) -> None:
    font = _get_bezel_font(max(MIN_FONT_SIZE, 16), bold=True)
    label = font.render("NETEXEC  BC-12", True, C_CHROME_LABEL)
    plate_w = label.get_width() + 16
    plate_h = label.get_height() + 6
    plate = pygame.Rect(x, cy - plate_h // 2, plate_w, plate_h)
    pygame.draw.rect(surface, C_CHROME_GROOVE, plate, border_radius=2)
    pygame.draw.rect(surface, C_CHROME_HI,     plate, 1, border_radius=2)
    surface.blit(label, (plate.x + 8, plate.y + 3))


def _draw_leds(surface: pygame.Surface, x: int, cy: int,
               tick_ms: int, on_air: bool) -> None:
    """Three status LEDs: red ON-AIR (blinks), amber, green."""
    blink = (tick_ms % BLINK_PERIOD_MS) < (BLINK_PERIOD_MS // 2)

    specs = [
        # (color_on, active)
        (C_LED_RED,   on_air and blink),
        (C_LED_AMBER, False),
        (C_LED_GREEN, True),
    ]

    labels = ["ON", "SB", "OK"]
    lfont  = _get_bezel_font(max(MIN_FONT_SIZE, 11))

    for i, ((col_on, active), lbl) in enumerate(zip(specs, labels)):
        lx = x + i * 22
        col = col_on if active else C_LED_OFF

        # Glow halo
        if active:
            glow = pygame.Surface((20, 20), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*col, _LED_GLOW_A), (10, 10), 9)
            surface.blit(glow, (lx - 3, cy - 10))

        pygame.draw.circle(surface, col,         (lx, cy), 5)
        pygame.draw.circle(surface, C_CHROME_HI, (lx, cy), 5, 1)

        lt = lfont.render(lbl, True, C_CHROME_LABEL)
        surface.blit(lt, (lx - lt.get_width() // 2, cy + 7))


def _draw_knob(surface: pygame.Surface, cx: int, cy: int) -> None:
    pygame.draw.circle(surface, C_CHROME_LO, (cx, cy), 9)
    pygame.draw.circle(surface, C_CHROME_HI, (cx, cy), 9, 1)
    # Indicator line at ~7 o'clock
    angle = math.radians(225)
    ex = int(cx + 6 * math.cos(angle))
    ey = int(cy + 6 * math.sin(angle))
    pygame.draw.line(surface, C_CHROME_HI, (cx, cy), (ex, ey), 1)


def _draw_vu_strip(surface: pygame.Surface, x: int, cy: int,
                   sw: int, tick_ms: int) -> None:
    """VU label + 8-segment bar + SIGNAL label."""
    lfont = _get_bezel_font(max(MIN_FONT_SIZE, 12), bold=True)
    sfont = _get_bezel_font(max(MIN_FONT_SIZE, 11))

    vu_lbl = lfont.render("VU", True, C_CHROME_LABEL)
    surface.blit(vu_lbl, (x, cy - vu_lbl.get_height() // 2))

    bar_x = x + vu_lbl.get_width() + 6
    seg_w = 7
    seg_h = 12
    seg_gap = 2
    n_segs = 8

    # Animate a gentle VU pulse so the console looks alive
    phase = (tick_ms % 2000) / 2000.0
    level = int(3 + 4 * (0.5 + 0.5 * math.sin(phase * 2 * math.pi)))

    for i in range(n_segs):
        sr = pygame.Rect(bar_x + i * (seg_w + seg_gap), cy - seg_h // 2, seg_w, seg_h)
        active = i < level
        col = (
            C_LED_RED   if i >= 6 else
            C_LED_AMBER if i >= 4 else
            C_LED_GREEN
        ) if active else C_CHROME_GROOVE
        pygame.draw.rect(surface, col, sr, border_radius=1)

    sig_x = bar_x + n_segs * (seg_w + seg_gap) + 6
    sig_lbl = sfont.render("SIGNAL", True, C_CHROME_LABEL)
    surface.blit(sig_lbl, (sig_x, cy - sig_lbl.get_height() // 2))
