"""
wildcard_show.py — NETEXEC
===========================
Wildcard show configuration modal — 3-step flow:
  Step 1: enter a name
  Step 2: pick one of 3 offered show types
  Step 3: pick one of 3 generated abilities, then confirm

Background is fully non-interactable: all click/tooltip regions accumulated
by render_game are cleared before the modal registers its own regions.
"""

import pygame

from engine.constants import (
    C_BG, C_CYAN, C_RED, C_RED_DIM, C_BORDER, C_WHITE,
    C_GREEN_DIM, C_GREY_MID,
    GENRE_COLORS,
)
from ..theme import C_TINT_GREEN_NOTCH, C_TINT_GREEN_SEL, C_TINT_TEAL_BADGE
from ..screen_enum import GameScreen
from ..widgets import draw_button, draw_modal_overlay, draw_label
from .base import Screen
from .wildcard_base import fmt_effect as _fmt_effect, cancel_btn as _cancel_btn

_MW = 580
_MH = 490




class WildcardShowScreen(Screen):
    def render(self, ctx, state):
        render(ctx, state)


def render(ctx, state):
    draw_modal_overlay(ctx)
    # Clear all background click/tooltip regions so nothing behind the modal fires.
    ctx._click_regions   = []
    ctx._tooltip_regions = []

    cx, cy = ctx._sw // 2, ctx._sh // 2
    modal  = pygame.Rect(cx - _MW // 2, cy - _MH // 2, _MW, _MH)
    pygame.draw.rect(ctx.screen, C_BG,   modal, border_radius=8)
    pygame.draw.rect(ctx.screen, C_CYAN, modal, 2, border_radius=8)

    step = ctx._wc_step
    step_labels = [
        "STEP 1 OF 3: NAME YOUR SHOW",
        "STEP 2 OF 3: CHOOSE SHOW TYPE",
        "STEP 3 OF 3: CHOOSE ABILITY",
    ]
    title = ctx._f("header").render(
        f"WILDCARD SHOW - {step_labels[step - 1]}", True, C_CYAN)
    ctx.screen.blit(title, title.get_rect(center=(cx, modal.y + 22)))

    y = modal.y + 48

    if step == 1:
        _step1(ctx, state, modal, cx, y)
    elif step == 2:
        _step2(ctx, state, modal, cx, y)
    else:
        _step3(ctx, state, modal, cx, y)


# ─── STEP 1: NAME ENTRY ───────────────────────────────────────────────────────

def _step1(ctx, state, modal, cx, y):
    draw_label(ctx, "SHOW NAME  (click field, then type):", modal.x + 16, y)
    y += 20
    nr = pygame.Rect(modal.x + 16, y, modal.width - 32, 30)
    pygame.draw.rect(ctx.screen, C_TINT_GREEN_NOTCH, nr)
    pygame.draw.rect(ctx.screen, C_CYAN if ctx._wc_input_active else C_BORDER, nr, 1)
    disp = (ctx._wc_name or "ENTER NAME...") + ("_" if ctx._wc_input_active else "")
    nt = ctx._f("body").render(disp[:30], True, C_WHITE if ctx._wc_name else C_GREEN_DIM)
    ctx.screen.blit(nt, (nr.x + 6, nr.y + 6))

    def _activate(): ctx._wc_input_active = True
    ctx._add_click(nr, _activate)
    y += 38

    hint = ctx._f("small").render("Leave blank to use ???", True, C_GREY_MID)
    ctx.screen.blit(hint, (modal.x + 16, y))

    btn_y = modal.bottom - 56
    next_rect = pygame.Rect(cx - 70, btn_y, 140, 38)

    def _next():
        ctx._wc_input_active  = False
        ctx._wc_offered_types = state.roll_wildcard_types()
        ctx._wc_genre         = None
        ctx._wc_step          = 2

    draw_button(ctx, next_rect, "NEXT ►", _next, border_color=C_CYAN)
    _cancel_btn(ctx, state, modal.right - 126, btn_y)


# ─── STEP 2: TYPE SELECTION ───────────────────────────────────────────────────

def _step2(ctx, state, modal, cx, y):
    name_disp = ctx._wc_name or "???"
    sub = ctx._f("small").render(f'Show: "{name_disp}"', True, C_GREEN_DIM)
    ctx.screen.blit(sub, sub.get_rect(center=(cx, y)))
    y += 28

    draw_label(ctx, "SELECT SHOW TYPE:", modal.x + 16, y)
    y += 22

    types = ctx._wc_offered_types or []
    if types:
        bw = (modal.width - 32 - (len(types) - 1) * 6) // len(types)
        for i, gid in enumerate(types):
            gr   = pygame.Rect(modal.x + 16 + i * (bw + 6), y, bw, 52)
            gsel = ctx._wc_genre == gid
            gcol = GENRE_COLORS.get(gid, (C_CYAN, C_TINT_TEAL_BADGE))
            pygame.draw.rect(ctx.screen, gcol[1] if gsel else C_BG, gr, border_radius=5)
            pygame.draw.rect(ctx.screen, gcol[0], gr, 2 if gsel else 1, border_radius=5)
            gt = ctx._f("body").render(gid, True, gcol[0])
            ctx.screen.blit(gt, gt.get_rect(center=gr.center))

            def _pick(g=gid): ctx._wc_genre = g
            ctx._add_click(gr, _pick)
    y += 68

    # Show the genre description if one is selected
    if ctx._wc_genre:
        from engine.cards import load_wildcards
        wc_cfg    = load_wildcards()
        genre_map = {g["id"]: g for g in wc_cfg["wildcard_show"]["genre_options"]}
        desc_text = genre_map.get(ctx._wc_genre, {}).get("desc", "")
        if desc_text:
            dsf = ctx._f("small").render(desc_text[:76], True, C_GREY_MID)
            ctx.screen.blit(dsf, dsf.get_rect(center=(cx, y)))

    btn_y = modal.bottom - 56

    def _back():
        ctx._wc_genre = None
        ctx._wc_step  = 1

    draw_button(ctx, pygame.Rect(modal.x + 16, btn_y, 90, 38),
                "◄ BACK", _back, border_color=C_GREY_MID, text_color=C_GREY_MID)

    if ctx._wc_genre:
        def _to_step3():
            ctx._wc_offered_abilities = state.roll_wildcard_abilities(
                ctx._wc_genre, card_type="show")
            ctx._wc_chosen_ability = None
            ctx._wc_step = 3

        draw_button(ctx, pygame.Rect(cx - 70, btn_y, 140, 38),
                    "NEXT ►", _to_step3, border_color=C_CYAN)

    _cancel_btn(ctx, state, modal.right - 126, btn_y)


# ─── STEP 3: ABILITY SELECTION ────────────────────────────────────────────────

def _step3(ctx, state, modal, cx, y):
    name_disp = ctx._wc_name or "???"
    sub = ctx._f("small").render(
        f'Show: "{name_disp}"  -  Type: {ctx._wc_genre}', True, C_GREEN_DIM)
    ctx.screen.blit(sub, sub.get_rect(center=(cx, y)))
    y += 28

    draw_label(ctx, "CHOOSE AN ABILITY:", modal.x + 16, y)
    y += 22

    for ab in (ctx._wc_offered_abilities or []):
        eff  = ab.get("effect", {})
        sel  = ctx._wc_chosen_ability is ab
        card = pygame.Rect(modal.x + 16, y, modal.width - 32, 82)
        pygame.draw.rect(ctx.screen, C_TINT_GREEN_SEL if sel else C_BG, card, border_radius=5)
        pygame.draw.rect(ctx.screen, C_CYAN if sel else C_BORDER,
                         card, 2 if sel else 1, border_radius=5)

        lbl = ctx._f("bold").render(ab.get("label", ""), True, C_WHITE)
        ctx.screen.blit(lbl, (card.x + 10, card.y + 8))

        desc_surf = ctx._f("small").render(ab.get("desc", "")[:74], True, C_GREEN_DIM)
        ctx.screen.blit(desc_surf, (card.x + 10, card.y + 30))

        eff_surf = ctx._f("small").render(_fmt_effect(eff), True, C_CYAN)
        ctx.screen.blit(eff_surf, (card.x + 10, card.y + 52))

        def _pick_ab(a=ab): ctx._wc_chosen_ability = a
        ctx._add_click(card, _pick_ab)
        y += 90

    btn_y = modal.bottom - 56

    def _back():
        ctx._wc_chosen_ability = None
        ctx._wc_step = 2

    draw_button(ctx, pygame.Rect(modal.x + 16, btn_y, 90, 38),
                "◄ BACK", _back, border_color=C_GREY_MID, text_color=C_GREY_MID)

    if ctx._wc_chosen_ability:
        def _confirm():
            result = state.resolve_wildcard_show(
                ctx._wc_name, ctx._wc_genre, ctx._wc_chosen_ability)
            if result["ok"]:
                ctx.set_screen(GameScreen.PLAYING)
                ctx._toast(result["message"], result["level"])
            else:
                ctx._toast(result["message"], "error")

        draw_button(ctx, pygame.Rect(cx - 70, btn_y, 140, 38),
                    "CONFIRM ►", _confirm, border_color=C_CYAN)

    _cancel_btn(ctx, state, modal.right - 126, btn_y)


# ─── SHARED ───────────────────────────────────────────────────────────────────

