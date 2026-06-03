"""
pause.py — NETEXEC
===================
Pause-menu overlay (rendered on top of the game background).
"""

import pygame

from engine.constants import C_BG, C_GREEN_BRIGHT
from ..screen_enum import GameScreen
from ..widgets import draw_button
from .base import Screen


class PauseScreen(Screen):
    def render(self, ctx, state):
        render(ctx, state)


def _open_settings(ctx):
    ctx._settings_return_screen = GameScreen.PAUSE
    ctx.set_screen(GameScreen.SETTINGS)


def render(ctx, state):
    ctx.screen.fill(C_BG)
    cx, cy = ctx._sw // 2, ctx._sh // 2

    mw, mh = 320, 300
    modal  = pygame.Rect(cx - mw // 2, cy - mh // 2, mw, mh)
    pygame.draw.rect(ctx.screen, C_BG,          modal, border_radius=8)
    pygame.draw.rect(ctx.screen, C_GREEN_BRIGHT, modal, 2, border_radius=8)

    pt = ctx._f("header").render("PAUSED", True, C_GREEN_BRIGHT)
    ctx.screen.blit(pt, pt.get_rect(center=(cx, modal.y + 26)))

    btns = [
        ("RESUME",        lambda: ctx.set_screen(GameScreen.PLAYING)),
        ("SAVE GAME",     lambda: ctx._save_game(state)),
        ("SETTINGS",      lambda: _open_settings(ctx)),
        ("QUIT TO MENU",  lambda: ctx.set_screen(GameScreen.MENU)),
    ]
    for i, (label, cb) in enumerate(btns):
        br = pygame.Rect(cx - 110, modal.y + 60 + i * 50, 220, 36)
        draw_button(ctx, br, label, cb)
