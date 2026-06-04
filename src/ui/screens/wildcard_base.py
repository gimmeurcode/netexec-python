"""
wildcard_base.py — NETEXEC
==========================
Shared helpers for the near-identical wildcard SHOW and AD configurator modals
(wildcard_show.py / wildcard_ad.py). Both 3-step flows format their generated
abilities the same way and use the same CANCEL button, so those live here as the
single source of truth.
"""

import pygame

from engine.constants import C_RED, C_RED_DIM
from ..screen_enum import GameScreen
from ..widgets import draw_button


def fmt_effect(eff: dict) -> str:
    """Format a generated wildcard ability dict as a concise one-line summary."""
    parts = []
    if "v_flat"  in eff: parts.append(f"+{eff['v_flat']} views")
    if "v_mult"  in eff: parts.append(f"{eff['v_mult']:.2f}x mult")
    if "income"  in eff: parts.append(f"+${eff['income']}/season")
    if "upkeep"  in eff: parts.append(f"{eff['upkeep']:+d} upkeep")
    return "  -  ".join(parts) if parts else "--"


def cancel_btn(ctx, state, x, y):
    """Draw the shared CANCEL button that clears the selection and exits."""
    def _cancel():
        state.clear_selection()
        ctx.set_screen(GameScreen.PLAYING)

    draw_button(ctx, pygame.Rect(x, y, 110, 38), "CANCEL", _cancel,
                border_color=C_RED_DIM, text_color=C_RED)
