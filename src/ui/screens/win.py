"""
win.py — NETEXEC
=================
Victory screen shown after all seasons are cleared — a celebration with star
confetti and a final-stats block, matching draw_win in netexec_reference.py.
"""

import math

import pygame

from engine.constants import (
    C_BG, C_GREEN_BRIGHT, C_GREEN_MID, C_AMBER, C_CYAN, C_WHITE,
    C_GREY_LIGHT, C_GREY_MID, C_NET_POS, MAX_SEASONS,
)
from ..screen_enum import GameScreen
from ..widgets import draw_button, draw_kv, line_step
from ..assets import draw_star_icon
from .base import Screen


class WinScreen(Screen):
    def render(self, ctx, state):
        render(ctx, state)


def render(ctx, state):
    cx, cy = ctx._sw // 2, ctx._sh // 2
    mw, mh = 660, min(460, ctx._sh - 80)
    modal  = pygame.Rect(cx - mw // 2, cy - mh // 2, mw, mh)
    pygame.draw.rect(ctx.screen, C_BG, modal, border_radius=8)
    pygame.draw.rect(ctx.screen, C_GREEN_BRIGHT, modal, 2, border_radius=8)

    # Twinkling star confetti around the panel edges.
    t = ctx._tick_ms
    confetti = [(-300, 60, C_AMBER), (300, 90, C_GREEN_BRIGHT),
                (-270, 360, C_CYAN), (300, 330, C_AMBER),
                (-320, 210, C_GREEN_MID), (320, 220, C_AMBER)]
    for i, (dx, dy, col) in enumerate(confetti):
        r = 7 + (i % 3) * 2 + int(2 * math.sin(t * 0.004 + i))
        sx, sy = modal.centerx + dx, modal.y + dy
        if 0 <= sx < ctx._sw and 0 <= sy < ctx._sh:
            draw_star_icon(ctx.screen,
                           pygame.Rect(sx - r, sy - r, r * 2, r * 2), col, filled=True)

    y = modal.y + 26
    title = ctx._f("title").render("SEASON CLEARED", True, C_GREEN_BRIGHT)
    ctx.screen.blit(title, title.get_rect(center=(cx, y + 14)))
    y += title.get_height() + 14

    sub = ctx._f("header").render(
        f"You survived all {MAX_SEASONS} seasons as Network Executive.",
        True, C_WHITE)
    ctx.screen.blit(sub, sub.get_rect(center=(cx, y)))
    y += line_step(ctx._f("header"), 1.0) + 18

    f_sm  = ctx._f("small")
    col_w = max(f_sm.size(k)[0] for k in
                ("FINAL VIEWS:", "PEAK NET INCOME:", "PRESTIGE EARNED:",
                 "DIFFICULTY:", "FINAL BUDGET:")) + 16
    x = cx - 170
    rows = [
        ("FINAL VIEWS:",   f"{state.total_views:,}",        C_WHITE),
        ("FINAL BUDGET:",  f"${state.budget:,.0f}",          C_AMBER),
        ("PRESTIGE EARNED:", f"+{state.network_prestige}",  C_AMBER),
        ("DIFFICULTY:",    str(state.difficulty),            C_GREY_LIGHT),
    ]
    for key, val, vc in rows:
        y = draw_kv(ctx, key, val, x, y, f_sm, C_GREY_MID, vc, col_w=col_w)

    y += 20
    note = ctx._f("micro").render(
        "Prestige carries into your next run with steeper quotas.",
        True, C_GREY_MID)
    ctx.screen.blit(note, note.get_rect(center=(cx, y)))

    # NEW GAME+ / QUIT TO MENU.
    nr = pygame.Rect(cx - 210, modal.bottom - 56, 195, 40)
    mr = pygame.Rect(cx + 15,  modal.bottom - 56, 195, 40)

    def _new_run():
        ctx._gameover_state  = None
        ctx._pending_new_run = True
        ctx.set_screen(GameScreen.DIFFICULTY)

    def _menu():
        ctx._gameover_state = None
        ctx.set_screen(GameScreen.MENU)

    draw_button(ctx, nr, "NEW GAME+ >", _new_run, border_color=C_GREEN_BRIGHT,
                text_color=C_WHITE)
    draw_button(ctx, mr, "MAIN MENU", _menu, border_color=C_GREEN_MID)
