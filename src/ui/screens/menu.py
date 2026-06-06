"""
menu.py — NETEXEC
==================
Title-screen renderer: animated logo, prestige info, navigation buttons.
"""

import math
import pygame

from engine.constants import (
    C_GREEN_MID, C_GREEN_DIM, C_AMBER, C_BORDER,
)
from saves import has_save
from ..screen_enum import GameScreen
from ..widgets import draw_button
from .base import Screen


class MenuScreen(Screen):
    def render(self, ctx, state):
        render(ctx, state)


def _open_settings(ctx):
    ctx._settings_return_screen = GameScreen.MENU
    ctx.set_screen(GameScreen.SETTINGS)


def render(ctx, state):
    cx = ctx._sw // 2
    cy = ctx._sh // 2

    # Animated logo — brightness oscillates between dim and bright
    brightness = int(200 + 55 * math.sin(ctx._menu_logo_phase))
    logo_col   = (0, brightness, int(brightness * 0.25))

    title = ctx._f("title").render("NETEXEC", True, logo_col)
    sub   = ctx._f("header").render("NETWORK EXECUTIVE SIMULATOR", True, C_GREEN_MID)
    ctx.screen.blit(title, title.get_rect(center=(cx, cy - 120)))
    ctx.screen.blit(sub,   sub.get_rect(center=(cx, cy - 70)))

    pygame.draw.line(ctx.screen, C_BORDER, (cx - 300, cy - 50), (cx + 300, cy - 50), 1)

    if state.network_prestige > 0:
        pt = ctx._f("small").render(
            f"NETWORK PRESTIGE: {state.network_prestige}  |  RUN: {state.run}",
            True, C_AMBER,
        )
        ctx.screen.blit(pt, pt.get_rect(center=(cx, cy - 30)))

    btns = [
        ("RESUME GAME", lambda: ctx._resume_game(state)) if has_save(0) else None,
        ("NEW RUN",     lambda: ctx._start_new_game(state, new_run=False)),
        ("CONTINUE",    lambda: ctx._start_new_game(state, new_run=True)) if state.network_prestige > 0 else None,
        ("SETTINGS",    lambda: _open_settings(ctx)),
        ("QUIT",        lambda: pygame.event.post(pygame.event.Event(pygame.QUIT))),
    ]
    btns = [b for b in btns if b is not None]

    btn_w, btn_h = 280, 44
    for i, (label, cb) in enumerate(btns):
        by   = cy + 10 + i * (btn_h + 10)
        rect = pygame.Rect(cx - btn_w // 2, by, btn_w, btn_h)
        draw_button(ctx, rect, label, cb)

    try:
        from version import VERSION
        ver_str = f"v{VERSION}"
    except Exception:
        ver_str = "v1.1.0"
    ver = ctx._f("micro").render(ver_str, True, C_GREEN_DIM)
    ctx.screen.blit(ver, ver.get_rect(bottomright=(ctx._sw - 10, ctx._sh - 6)))
