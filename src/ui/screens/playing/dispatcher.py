"""
playing/dispatcher.py — NETEXEC
===============================
Main game screen: broadcast schedule, acquisition terminal, season header.

Public entry points
-------------------
  render(ctx, state)
      Full PLAYING screen render: game panels + optional show-detail modal
      or tutorial overlay.

  render_game(ctx, state)
      Render only the game background (header + left + right panels).
      Called by overlay screens (PAUSE, SUMMARY, WILDCARD_*) that need the
      game drawn underneath their modal layer.
"""

import pygame

from ..base import Screen
from .header import _draw_header
from .schedule import _draw_left_panel
from .shop import _draw_right_panel
from .detail import _draw_show_detail_modal
from ...ledger import Ledger


class PlayingScreen(Screen):
    def render(self, ctx, state):
        render(ctx, state)


# ─── PUBLIC RENDER ENTRY POINTS ──────────────────────────────────────────────

def render(ctx, state):
    """Render the full PLAYING screen."""
    render_game(ctx, state)
    if ctx._show_detail:
        ctx._click_regions   = []  # block all background clicks
        ctx._tooltip_regions = []  # block all background tooltips
        ctx._hover_ttip_key  = ""  # reset hover state so no stale tooltip lingers
        _draw_show_detail_modal(ctx, state)
    elif ctx._tutorial:
        ctx._tutorial.draw(ctx.screen, ctx._fonts)


def render_game(ctx, state):
    """Draw the game background: header + left panel + right panel (or ledger)."""
    _draw_header(ctx, state)
    _draw_left_panel(ctx, state)
    if getattr(ctx, "_show_ledger", False):
        Ledger.draw(ctx, state)
    else:
        _draw_right_panel(ctx, state)
