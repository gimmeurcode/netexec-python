"""
game_over.py — NETEXEC
=======================
Win / loss end-screen renderer.
"""

import pygame

from engine.constants import (
    C_GREEN_BRIGHT, C_GREEN_MID, C_AMBER, C_RED, C_WHITE,
    MAX_SEASONS,
)
from ..screen_enum import GameScreen
from ..widgets import draw_button
from .base import Screen


class GameOverScreen(Screen):
    def render(self, ctx, state):
        render(ctx, state)


def render(ctx, state):
    cx, cy = ctx._sw // 2, ctx._sh // 2
    won    = ctx._gameover_state == "win"

    flash_col = C_GREEN_BRIGHT if won else C_RED
    big_title = "SYNDICATION SUCCESS" if won else "NETWORK ICED"

    title_surf = ctx._f("title").render(big_title, True, flash_col)
    ctx.screen.blit(title_surf, title_surf.get_rect(center=(cx, cy - 130)))

    stats = [
        f"FINAL VIEWS:   {state.total_views:,}",
        f"SEASONS AIRED: {state.season}/{MAX_SEASONS}",
        f"PRESTIGE LEVEL:{state.network_prestige}",
        f"DIFFICULTY:    {state.difficulty}",
        f"FINAL BUDGET:  ${state.budget:,}",
    ]
    for i, st in enumerate(stats):
        col   = C_WHITE if i % 2 == 0 else C_GREEN_MID
        s_surf = ctx._f("body").render(st, True, col)
        ctx.screen.blit(s_surf, s_surf.get_rect(center=(cx, cy - 60 + i * 26)))

    if won:
        win_msg = "THE BOARD SENDS ITS CONGRATULATIONS. PRESTIGE UNLOCKED."
        wt = ctx._f("header").render(win_msg, True, C_AMBER)
        ctx.screen.blit(wt, wt.get_rect(center=(cx, cy + 80)))
    else:
        loss_msg = "YOUR CONTRACT HAS BEEN TERMINATED. A REALITY SHOW WILL FILL YOUR SLOT."
        lt = ctx._f("body").render(loss_msg, True, C_RED)
        ctx.screen.blit(lt, lt.get_rect(center=(cx, cy + 80)))

    nr_rect   = pygame.Rect(cx - 160, cy + 130, 145, 44)
    menu_rect = pygame.Rect(cx + 20,  cy + 130, 145, 44)

    def _new_run():
        ctx._gameover_state  = None
        ctx.set_screen(GameScreen.DIFFICULTY)
        ctx._pending_new_run = True

    def _menu():
        ctx._gameover_state = None
        ctx.set_screen(GameScreen.MENU)

    draw_button(ctx, nr_rect,   "NEW RUN >",  _new_run, border_color=C_GREEN_BRIGHT)
    draw_button(ctx, menu_rect, "MAIN MENU",        _menu,    border_color=C_GREEN_MID)
