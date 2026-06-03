"""
difficulty.py — NETEXEC
========================
Four-card difficulty selection screen.
"""

import pygame

from engine.constants import (
    C_GREEN_BRIGHT, C_GREEN_MID, C_GREEN_PANEL, C_AMBER_DIM,
    DIFFICULTY_LEVELS,
)
from ..screen_enum import GameScreen
from ..widgets import draw_button, draw_text_wrapped
from .base import Screen


class DifficultyScreen(Screen):
    def render(self, ctx, state):
        render(ctx, state)


def render(ctx, state):
    cx  = ctx._sw // 2
    cy  = ctx._sh // 2
    hdr = ctx._f("header").render("SELECT DIFFICULTY", True, C_GREEN_BRIGHT)
    ctx.screen.blit(hdr, hdr.get_rect(center=(cx, 60)))

    card_w, card_h = 260, 345
    keys    = ["EASY", "NORMAL", "HARD", "BRUTAL"]
    total_w = len(keys) * card_w + (len(keys) - 1) * 18
    start_x = cx - total_w // 2

    for i, key in enumerate(keys):
        diff = DIFFICULTY_LEVELS[key]
        x    = start_x + i * (card_w + 18)
        y    = cy - card_h // 2 + 20
        rect = pygame.Rect(x, y, card_w, card_h)
        dcol = diff["color"]

        pygame.draw.rect(ctx.screen, C_GREEN_PANEL, rect, border_radius=6)
        pygame.draw.rect(ctx.screen, dcol,          rect, 2, border_radius=6)

        lbl = ctx._f("header").render(diff["label"], True, dcol)
        ctx.screen.blit(lbl, lbl.get_rect(center=(rect.centerx, y + 30)))

        stats = [
            f"Budget mod:  {'+' if diff['budget_mod'] >= 0 else ''}{diff['budget_mod']}$",
            f"Target:       x{diff['target_mult']:.2f}",
            f"Growth:      {'+' if diff['growth_mod'] >= 0 else ''}{diff['growth_mod']:.2f}",
            f"Star cost:   x{diff['star_cost_mult']:.2f}",
            f"Ad income:   x{diff['ad_income_mult']:.2f}",
            f"Rival pres.: +{diff['rival_pressure']}",
        ]
        for j, s in enumerate(stats):
            st = ctx._f("small").render(s, True, C_GREEN_MID)
            ctx.screen.blit(st, (x + 12, y + 58 + j * 20))

        draw_text_wrapped(
            ctx.screen,
            diff["desc"],
            pygame.Rect(x + 10, y + 182, card_w - 20, 100),
            ctx._f("micro"), C_AMBER_DIM,
        )

        btn_rect = pygame.Rect(x + 20, y + card_h - 52, card_w - 40, 38)
        sel_key  = key
        pending  = getattr(ctx, "_pending_new_run", False)

        def _select(dk=sel_key, pnr=pending):
            state.start_new_run(increment_run=pnr, difficulty=dk)
            ctx.set_screen(GameScreen.PLAYING)
            if ctx.audio:
                ctx.audio.start_bg_music()
            ctx._toast("GOOD LUCK, EXECUTIVE.", "success")
            show_tut = (
                (state.run == 1 and not ctx._tutorial_done)
                or ctx._replay_tutorial_requested
            )
            if show_tut:
                from ..tutorial import TutorialController
                ctx._tutorial = TutorialController()
                ctx._replay_tutorial_requested = False

        draw_button(ctx, btn_rect, "SELECT", _select, border_color=dcol)

    back_rect = pygame.Rect(20, 20, 100, 36)
    draw_button(ctx, back_rect, "< BACK",
                lambda: ctx.set_screen(GameScreen.MENU))
