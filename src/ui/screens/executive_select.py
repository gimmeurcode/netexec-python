"""
executive_select.py — NETEXEC
==============================
Executive-selection screen shown after difficulty, before a run starts.

The player is offered 3 of the 7 executives (drawn with ``draw_executive_offers``)
and must choose one. Each executive applies a persistent, run-long bundle of
effects, so the choice meaningfully changes how the whole game plays out. Because
only 3 of 7 are offered each new game, the player cannot always pick the same one.
"""

import pygame

from engine.constants import (
    C_GREEN_BRIGHT, C_GREEN_MID, C_GREEN_PANEL, C_AMBER_DIM,
    C_WHITE, C_RED, C_CYAN,
)
from ..screen_enum import GameScreen
from ..widgets import draw_button, draw_text_wrapped
from .base import Screen


def _effect_lines(effects: dict) -> list:
    """Build short, human-readable bullet lines summarising an executive's effects.

    Returns list of (text, is_bonus) tuples; is_bonus toggles colour
    (green for upside, red for downside) so tradeoffs read at a glance.
    """
    pm    = effects.get("passive_mods", {})
    lines = []

    def add(text, good):
        lines.append((text, good))

    sb = effects.get("start_budget_delta", 0)
    if sb:
        add(f"Start budget {'+' if sb > 0 else ''}{sb}$", sb > 0)
    bps = effects.get("budget_per_season", 0)
    if bps:
        add(f"{'+' if bps > 0 else ''}{bps}$ per season", bps > 0)

    vm = pm.get("view_mult", 1.0)
    if vm != 1.0:
        add(f"All views x{vm:.2f}", vm > 1.0)
    um = pm.get("upkeep_mult", 1.0)
    if um != 1.0:
        add(f"All upkeep x{um:.2f}", um < 1.0)
    inc = pm.get("income_flat", 0)
    if inc:
        add(f"{'+' if inc > 0 else ''}{inc}$ income / show", inc > 0)

    for genre, mult in pm.get("genre_view_mult", {}).items():
        if mult != 1.0:
            add(f"{genre.title()} views x{mult:.2f}", mult > 1.0)

    tm = effects.get("target_mult", 1.0)
    if tm != 1.0:
        # Lower quotas (<1) are good for the player.
        add(f"Quotas x{tm:.2f}", tm < 1.0)
    rr = effects.get("reroll_cost_mult", 1.0)
    if rr != 1.0:
        add(f"Reroll cost x{rr:.2f}", rr < 1.0)

    return lines


class ExecutiveSelectScreen(Screen):
    def render(self, ctx, state):
        render(ctx, state)


def _ensure_offers(ctx):
    offers = getattr(ctx, "_exec_offers", None)
    if not offers:
        from engine import cards
        offers = cards.draw_executive_offers(3)
        ctx._exec_offers = offers
    return offers


def render(ctx, state):
    cx  = ctx._sw // 2
    offers = _ensure_offers(ctx)

    hdr = ctx._f("header").render("CHOOSE YOUR EXECUTIVE", True, C_GREEN_BRIGHT)
    ctx.screen.blit(hdr, hdr.get_rect(center=(cx, 46)))

    diff = getattr(ctx, "_pending_difficulty", state.difficulty)
    sub  = ctx._f("small").render(
        f"DIFFICULTY: {diff}   -   pick 1 of 3 (drawn from 7)", True, C_AMBER_DIM)
    ctx.screen.blit(sub, sub.get_rect(center=(cx, 74)))

    card_w, card_h = 300, 430
    n       = len(offers)
    total_w = n * card_w + (n - 1) * 22
    start_x = cx - total_w // 2
    top     = 100

    for i, ex in enumerate(offers):
        x    = start_x + i * (card_w + 22)
        rect = pygame.Rect(x, top, card_w, card_h)

        pygame.draw.rect(ctx.screen, C_GREEN_PANEL, rect, border_radius=6)
        pygame.draw.rect(ctx.screen, C_CYAN,        rect, 2, border_radius=6)

        title = ctx._f("header").render(ex.get("title", "?"), True, C_CYAN)
        ctx.screen.blit(title, title.get_rect(center=(rect.centerx, top + 28)))
        name = ctx._f("small").render(ex.get("name", ""), True, C_WHITE)
        ctx.screen.blit(name, name.get_rect(center=(rect.centerx, top + 52)))

        draw_text_wrapped(
            ctx.screen, ex.get("desc", ""),
            pygame.Rect(x + 12, top + 72, card_w - 24, 120),
            ctx._f("micro"), C_AMBER_DIM,
        )

        ey = top + 196
        for text, good in _effect_lines(ex.get("effects", {})):
            col = C_GREEN_MID if good else C_RED
            bullet = ctx._f("small").render(("+ " if good else "- ") + text, True, col)
            ctx.screen.blit(bullet, (x + 16, ey))
            ey += 20

        btn_rect = pygame.Rect(x + 20, top + card_h - 50, card_w - 40, 38)

        def _choose(execu=ex):
            state.start_new_run(
                increment_run=getattr(ctx, "_pending_new_run_flag", False),
                difficulty=getattr(ctx, "_pending_difficulty", None),
                seed=getattr(ctx, "_pending_seed", None),
                executive=execu,
            )
            ctx.set_screen(GameScreen.PLAYING)
            if ctx.audio:
                ctx.audio.start_bg_music()
            ctx._toast(f"{execu.get('title', 'EXECUTIVE').upper()} TAKES THE HELM.", "success")
            show_tut = (
                (state.run == 1 and not ctx._tutorial_done)
                or ctx._replay_tutorial_requested
            )
            if show_tut:
                from ..tutorial import TutorialController
                ctx._tutorial = TutorialController()
                ctx._replay_tutorial_requested = False

        draw_button(ctx, btn_rect, "CHOOSE", _choose, border_color=C_CYAN)

    back_rect = pygame.Rect(20, 20, 100, 36)
    draw_button(ctx, back_rect, "< BACK",
                lambda: ctx.set_screen(GameScreen.DIFFICULTY))
